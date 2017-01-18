#!/usr/bin/env python

import os
import sys
import time
import json
import shutil
import argparse
from os import path
from bayes_opt import BayesianOptimization
from subprocess import Popen, check_output, check_call
import math
from collections import deque
import numpy as np
import read_search_log

local_pantheon = path.expanduser('~/pantheon')
local_test_dir = path.join(local_pantheon, 'test')
local_analyze_dir = path.join(local_pantheon, 'analyze')
local_replication_dir = path.abspath(path.dirname(__file__))

args = {}


def create_empty_directory(dir_path):
    try:
        shutil.rmtree(dir_path)
    except:
        pass

    try:
        os.makedirs(dir_path)
    except:
        pass


def copy_logs(args, ip_dict):
    logs_dir = path.join(local_replication_dir, 'candidate_results')
    create_empty_directory(logs_dir)

    copy_procs = []
    for ip in args['ips']:
        if ip not in ip_dict:
            continue

        run_id = ip_dict[ip][0]
        cc = ip_dict[ip][1]

        logs_to_copy = '%s*run%s.log' % (cc, run_id)
        logs_to_copy = 'ubuntu@%s:~/pantheon/test/%s' % (ip, logs_to_copy)
        cmd = 'scp %s %s' % (logs_to_copy, logs_dir)
        sys.stderr.write('+ %s\n' % cmd)
        copy_procs.append(Popen(cmd, shell=True))

    for proc in copy_procs:
        proc.wait()

    return logs_dir


def create_metadata_file(args, logs_dir):
    metadata = {}
    metadata['cc_schemes'] = ' '.join(args['schemes'])
    metadata['runtime'] = 30
    metadata['flows'] = 1
    metadata['interval'] = 0
    metadata['sender_side'] = 'local'
    metadata['run_times'] = 5

    metadata_path = path.join(logs_dir, 'pantheon_metadata.json')
    with open(metadata_path, 'w') as metadata_file:
        json.dump(metadata, metadata_file)


def get_best_score(args, score_name):
    if score_name == 'best_tput_median_score':
        dir_name = args['location'] + 'best_tput_median_results'
        search_str = 'Average median throughput difference'
    elif score_name == 'best_delay_median_score':
        dir_name = args['location'] + 'best_delay_median_results'
        search_str = 'Average median delay difference'
    elif score_name == 'best_overall_median_score':
        dir_name = args['location'] + 'best_overall_median_results'
        search_str = 'Average median difference for throughput and delay'

    best_results_path = path.join(local_replication_dir, dir_name)
    score_path = path.join(best_results_path, 'comparison_result')
    best_score = sys.maxint

    if not path.isfile(score_path):
        return best_score

    score_file = open(score_path)

    while True:
        line = score_file.readline()
        if not line:
            break

        if search_str in line:
            score_str = score_file.readline()
            best_score = float(score_str[:-2])
            break

    score_file.close()
    return best_score


def replication_score(args, logs_dir):
    compare_src = path.join(local_analyze_dir, 'compare_two_experiments.py')
    real_logs = args['replicate']
    cmd = ['python', compare_src, real_logs, logs_dir, '--analyze-schemes',
           ' '.join(args['schemes'])]
    sys.stderr.write('+ %s\n' % ' '.join(cmd))
    results = check_output(cmd)

    result_path = path.join(logs_dir, 'comparison_result')
    with open(result_path, 'w') as result_file:
        result_file.write(results)

    scores = results.split('\n')
    tput_median_score = float(scores[-6][:-1])
    delay_median_score = float(scores[-4][:-1])
    overall_median_score = float(scores[-2][:-1])

    sys.stderr.write('scores: %s %s %s\n' %
                     (scores[-6], scores[-4], scores[-2]))
    return (tput_median_score, delay_median_score, overall_median_score)


def save_best_results(logs_dir, dst_dir):
    try:
        shutil.rmtree(dst_dir)
    except:
        pass

    cmd = 'cp -r %s %s' % (logs_dir, dst_dir)
    check_call(cmd, shell=True)


def serialize(args, scores):
    return ('bandwidth=%.2f,delay=%d,uplink_queue=%d,uplink_loss=%.4f,'
            'downlink_loss=%.4f,tput_median_score=%s,delay_median_score=%s,'
            'overall_median_score=%s\n'
            % (args['bandwidth'][0],
               args['delay'][0],
               args['uplink_queue'][0],
               args['uplink_loss'][0],
               args['downlink_loss'][0],
               scores[0], scores[1], scores[2]))


def clean_up_processes(args):
    # kill all pantheon and iperf processes on proxies
    setup_procs = []
    for ip in args['ips']:
        ssh_cmd = ['ssh', 'ubuntu@%s' % ip]

        cmd = ssh_cmd + [
                'pkill -f pantheon && pkill -f iperf && pkill -f mm-link && '
                'pkill -f mm-delay && pkill -f mm-loss']
        sys.stderr.write('+ %s\n' % ' '.join(cmd))
        setup_procs.append(Popen(cmd))

    for proc in setup_procs:
        proc.wait()


def run_experiment(args):
    default_schemes = ['default_tcp', 'vegas', 'ledbat', 'pcc', 'verus',
                       'scream', 'sprout', 'webrtc', 'quic']
    if args['pkill']:
        clean_up_processes(args)

    run_proxy = '~/replication_with_emulation/run_proxy.py'

    proxy_procs = []
    ip_dict = {}

    params = []
    params += ['--bandwidth', ','.join(map(str, args['bandwidth']))]
    params += ['--delay', ','.join(map(str, args['delay']))]
    params += ['--uplink-queue', ','.join(map(str, args['uplink_queue']))]
    params += ['--uplink-loss', ','.join(map(str, args['uplink_loss']))]
    params += ['--downlink-loss', ','.join(map(str, args['downlink_loss']))]

    ip_index = 0
    for run_id in xrange(1, 6):
        for cc in args['schemes']:
            ip = args['ips'][ip_index]
            ip_index = ip_index + 1
            ip_dict[ip] = (run_id, cc)
            ssh_cmd = ['ssh', 'ubuntu@%s' % ip]
            cmd = ssh_cmd + ['python', run_proxy] + params
            cmd += ['--run-id', '%s,%s' % (run_id, run_id)]
            cmd += ['--schemes %s' % cc]

            sys.stderr.write('+ %s\n' % ' '.join(cmd))
            proxy_procs.append(Popen(cmd))

    for proc in proxy_procs:
        proc.wait()

    logs_dir = copy_logs(args, ip_dict)
    create_metadata_file(args, logs_dir)
    scores = replication_score(args, logs_dir)

    if 'search_log' in args:
        args['search_log'].write(serialize(args, scores))

    if scores[0] < args['best_tput_median_score']:
        args['best_tput_median_score'] = scores[0]
        save_best_results(logs_dir, path.join(
            local_replication_dir,
            args['location'] + 'best_tput_median_results'))

    if scores[1] < args['best_delay_median_score']:
        args['best_delay_median_score'] = scores[1]
        save_best_results(logs_dir, path.join(
            local_replication_dir,
            args['location'] + 'best_delay_median_results'))

    if scores[2] < args['best_overall_median_score']:
        args['best_overall_median_score'] = scores[2]
        save_best_results(logs_dir, path.join(
            local_replication_dir,
            args['location'] + 'best_overall_median_results'))

    return scores

def setup_replication(args):
    setup_procs = []
    for ip in args['ips']:
        ssh_cmd = ['ssh', 'ubuntu@%s' % ip]

        cmd = ssh_cmd + ['cd ~/replication_with_emulation && git pull && '
                         'git checkout bayes_opt']
        sys.stderr.write('+ %s\n' % ' '.join(cmd))
        setup_procs.append(Popen(cmd))

    for proc in setup_procs:
        proc.wait()


def setup_pantheon(args):
    setup_procs = []
    for ip in args['ips']:
        ssh_cmd = ['ssh', 'ubuntu@%s' % ip]

        cmd = ssh_cmd + ['cd ~/pantheon/test && ./run.py --run-only setup']
        sys.stderr.write('+ %s\n' % ' '.join(cmd))
        setup_procs.append(Popen(cmd))

    for proc in setup_procs:
        proc.wait()


def get_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'ips', metavar='IP', nargs='+', help='proxy\'s IP address')
    parser.add_argument(
        '--max-iters', metavar='N', action='store', dest='max_iters',
        type=int, default=1, help='max iterations (default 1)')
    parser.add_argument('--setup-replication', action='store_true',
                        dest='setup_replication')
    parser.add_argument('--setup-pantheon', action='store_true',
                        dest='setup_pantheon')
    parser.add_argument('--include-pkill', action='store_true', dest='pkill')
    parser.add_argument(
        '--location',
        help='location to replicate (used in saved file/folder names)')
    parser.add_argument(
        '--replicate', metavar='LOG-PATH', required=True,
        help='logs of real world experiment to replicate')
    prog_args = parser.parse_args()

    args['ips'] = prog_args.ips

    args['max_iters'] = prog_args.max_iters
    args['replicate'] = prog_args.replicate

    if prog_args.location:
        args['location'] = prog_args.location + '_'
    else:
        args['location'] = ''

    args['schemes'] = ['default_tcp', 'vegas', 'ledbat', 'pcc', 'verus',
                       'scream', 'sprout', 'webrtc', 'quic']
    args['best_tput_median_score'] = get_best_score(
            args, 'best_tput_median_score')
    args['best_delay_median_score'] = get_best_score(
            args, 'best_delay_median_score')
    args['best_overall_median_score'] = get_best_score(
            args, 'best_overall_median_score')

    if prog_args.setup_replication:
        setup_replication(args)
    if prog_args.setup_pantheon:
        setup_pantheon(args)

    args['pkill'] = False
    if prog_args.pkill:
        args['pkill'] = True


def gain_function(bandwidth, delay, uplink_queue, uplink_loss, downlink_loss):
    global args

    args['bandwidth'] = (bandwidth, 0)
    args['delay'] = (delay, 0)
    args['uplink_queue'] = (uplink_queue, 0)
    args['uplink_loss'] = (uplink_loss, 0)
    args['downlink_loss'] = (downlink_loss, 0)

    scores = run_experiment(args)
    return gain(scores, bandwidth, delay, uplink_queue, uplink_loss, downlink_loss)

def gain(scores, bandwidth, delay, uplink_queue, uplink_loss, downlink_loss):
    global args
    # penalize if the scores are near the bounds
    max_bw = args["bounds"]["bandwidth"][0]
    min_bw = args["bounds"]["bandwidth"][1]
    min_queue = args["bounds"]["uplink_queue"][0]
    max_queue = args["bounds"]["uplink_queue"][1]
    max_loss = args["bounds"]["uplink_loss"][1]
    # check if the bandwidth is within a percentage of the bounds and penalize that
    penalty = 0
    if (((max_bw - bandwidth)/max_bw < .2) or ( (bandwidth - min_bw)/min_bw < .2 )):
        penalty -= 20
    if (( max_queue - uplink_queue )/max_queue < .2  or (uplink_queue - min_queue)/min_queue < .2 ):
        penalty -= 20

    if( ( max_loss - uplink_loss )/max_loss < .2 or ( max_loss - downlink_loss )/max_loss < .2):
        penalty -= 20
    # if either delay or throughput is bad, penalize that as well
    if scores[0] > 40 or scores[1] > 40:
        penalty += - 10
    return ( penalty - scores[2]*3 )


def modify_args(bandwidth, delay, uplink_queue, uplink_loss, downlink_loss):
    global args
    args['bandwidth'] = (bandwidth, 0)
    args['delay'] = (delay, 0)
    args['uplink_queue'] = (uplink_queue, 0)
    args['uplink_loss'] = (uplink_loss, 0)
    args['downlink_loss'] = (downlink_loss, 0)

def modify_priors(priors, point, score):
    priors["target"].append(score)
    priors["bandwidth"].append(point[0])
    priors["delay"].append(point[1])
    priors["uplink_queue"].append(point[2])
    priors["uplink_loss"].append(point[3])
    priors["downlink_loss"].append(point[4])

def past_max_bound(current, max_bound):
    for i in range(len(current)):
        if current[i] > max_bound[i]:
            return True
    return False

def loss_function( args, theta):
    return gain_function( theta[0], theta[1], theta[2], theta[3], theta[4] )

def run_coordinate_descent(current_best_dict, score_to_beat):
    current_best = []
    for key in ["bandwidth", "delay", "upink_queue", "downlink_queue", "uplink_loss", "downlink_loss"]:
        current_best.append(current_best_dict[key])
    print "RUNNING COORDINATE DESCENT PART OF SEARCH NOW"
    print current_best, "Current best option from bayes algorithm"
    # we are aiming for ~ 15 % -> so take the difference of the score to beat and 15 % and scale
    difference = score_to_beat - 15
    # the step accordingly
    global args
    current_min = []
    current_max = []
    for key in ["bandwidth", "delay", "uplink_queue", "uplink_loss", "downlink_loss"]:
        current_min.append(args["bounds"][key][0])
        current_max.append(args["bounds"][key][1])

    theta_min = []
    theta_max = []
    step = []
    for i in range(len(current_best)):
        x = current_best[i]
        theta_min.append(max(current_min[i], .75*x))
        theta_max.append(min(current_max[i], 1.25*x))
        step_amt = min(int( 5 * difference), 10)
        if step_amt < 0:
            step_amt = 10
        step.append( (theta_max[i] - theta_min[i])/step_amt)
    print "ABOUT TO START COORDINATE DESCENT PART OF THE ALGORITHM"
    # now do coordinate descent search between the current min and the current max
    theta = current_best
    c = 0
    for i in xrange(args['max_iters'] * len(theta)):
        init_score = loss_function(args, theta)
        q = deque([(init_score, theta[c])])

        for direction in [0, 1]:
            theta_c = theta[c]

            s = init_score
            best_score_c = init_score
            while True:
                if direction == 0:
                    theta_c += step[c]
                    if theta_c > theta_max[c]:
                        break
                else:
                    theta_c -= step[c]
                    if theta_c < theta_min[c]:
                        break

                theta_new = np.copy(theta)
                theta_new[c] = theta_c
                score = loss_function(args, theta_new)

                if direction == 0:
                    q.append((score, theta_c))
                else:
                    q.appendleft((score, theta_c))

                if score < best_score_c:
                    best_score_c = score
                    s = score
                else:
                    s = 0.3 * s + 0.7 * score
                    if s > best_score_c + 10:
                        break

        if len(q) <= 5:
            best_theta_c = min(q)[1]
        else:
            best_avg_score = sys.maxint
            for qi in xrange(2, len(q) - 2):
                avg_score = 0.1 * q[qi - 2][0] + 0.2 * q[qi - 1][0] + \
                            0.4 * q[qi][0] + \
                            0.2 * q[qi + 1][0] + 0.1 * q[qi + 2][0]
                if avg_score < best_avg_score:
                    best_avg_score = avg_score
                    best_theta_c = q[qi][1]

        theta[c] = best_theta_c
        c = (c + 1) % len(theta)
    return best_theta_c


def get_initial_knowledge(bounds, step_size):
    global args
    # order: bandwidth, delay, queue, uplink loss, downlink loss
    min_bound = bounds["min"]
    max_bound = bounds["max"]
    step = bounds["step"]

    # given the bounds, try points around it
    priors = {
            "target": [],
            "bandwidth": [],
            "delay": [],
            "uplink_queue": [],
            "uplink_loss": [],
            "downlink_loss": []
    }

    # now loop through from min to max with a step size
    current = min_bound
    thetas_to_try = []
    for bw in [min_bound[0] + step[0]*i for i in range(step_size)]:
        for delay in [min_bound[1] + step[1]*i for i in range(step_size)]:
            for queue in [min_bound[2] + step[2]*i for i in range(step_size)]:
                for uploss in [min_bound[3] + step[3]*i for i in range(step_size)]:
                    for downloss in [min_bound[4] + step[4]*i for i in range(step_size)]:
                        modify_args(bw, delay, queue, uploss, downloss)
                        score = gain(run_experiment(args), bw, delay, queue, uploss, downloss)
                        modify_priors(priors, [bw, delay, queue, uploss, downloss], score)

    return priors


def modify_bounds(best_points, best_scores):

    bounds = {}
    params =  ["bandwidth", "delay", "uplink_queue", "uplink_loss", "downlink_loss"]
    for i in range(len(params)):
        choices = [point[i] for point in best_points]
        key = params[i]
        bounds[key] = (min(choices), max(choices))
    print bounds
    return bounds

def main():
    global args
    get_args(args)

    search_log_name = args['location'] + 'search_log'
    search_log = open(search_log_name, 'a', 0)
    args['search_log'] = search_log

    # define bounds:
    bounds = {
    "bandwidth": (2.07, 18.51),
    "delay": (38, 160),
    "uplink_queue": (10, 1270),
    "uplink_loss": (0, .1),
    "downlink_loss": (0, .1)
    }
    args["bounds"] = bounds
    priors = {"target": [], "bandwidth": [], "delay": [], "uplink_queue": [], "uplink_loss": [], "downlink_loss": []}

    min_bounds = []
    max_bounds = []
    step = []
    step_size = 5 # explore step_size^2 initial points
    for key in ["bandwidth", "delay", "uplink_queue", "uplink_loss", "downlink_loss"]:
        min_bounds.append(bounds[key][0])
        max_bounds.append(bounds[key][1])
        step_val = (bounds[key][1] - bounds[key][0])/step_size # step size
        step.append(step_val)
    #priors = get_initial_knowledge({"min": min_bounds, "max": max_bounds, "step": step}, step_size)

    bo = BayesianOptimization( gain_function, bounds )
    bo.initialize(priors)
    bo.maximize(init_points=15, n_iter=args['max_iters'])
    search_log.close()
    best_three_points, best_scores = read_search_log.get_best_n(3, search_log_name)

    new_bounds = modify_bounds( best_three_points, best_scores )
    priors = read_search_log.parse_search_log_for_priors(priors, search_log_name)
 
    print best_three_points

    print bo.res['max']

    score_to_beat = bo.res['max']['max_val']
    theta_to_beat = bo.res['max']['max_params']

    #score_to_beat = 30
    #theta_to_beat = [9.26, 95, 600, 0, 0]
    #best_theta = run_coordinate_descent(theta_to_beat, score_to_beat)
    print "NOW DOING THE SECOND ROUND OF BAYESIAN OPTIMIZATION BASED ON RESULTS FROM THE FIRST ROUND"
    print priors
    new_search_log = open(search_log_name, 'a', 0)
    args["search_log"] = new_search_log
    bo2 = BayesianOptimization( gain_function, new_bounds )
    bo2.initialize(priors)


    bo2.maximize(init_points = 5, n_iter = args['max_iters'])

    print bo2.res['max']
    sys.stderr.write('Best tput median score: %s%%\n' %
                     args['best_tput_median_score'])
    sys.stderr.write('Best delay median score: %s%%\n' %
                     args['best_delay_median_score'])
    sys.stderr.write('Best overall median score: %s%%\n' %
                     args['best_overall_median_score'])
    new_search_log.close()

if __name__ == '__main__':
    main()
