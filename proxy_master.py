#!/usr/bin/env python

import os
import sys
import time
import json
import math
import shutil
import argparse
import numpy as np
from os import path
from subprocess import Popen, check_output, check_call

local_pantheon = path.expanduser('~/pantheon')
local_test_dir = path.join(local_pantheon, 'test')
local_analyze_dir = path.join(local_pantheon, 'analyze')
local_replication_dir = path.abspath(path.dirname(__file__))


def create_empty_directory(dir_path):
    try:
        shutil.rmtree(dir_path)
    except:
        pass

    try:
        os.makedirs(dir_path)
    except:
        pass


def copy_logs(args, ip_dict, logs_dir):
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
    float_scores = []
    float_scores.append(float(scores[-6][:-1]))
    float_scores.append(float(scores[-4][:-1]))
    float_scores.append(float(scores[-2][:-1]))

    sys.stderr.write('scores: %s %s %s\n' %
                     (scores[-6], scores[-4], scores[-2]))

    for i in range(0, 3):
        if math.isnan(float_scores[i]):
            float_scores[i] = 10000.0

    return tuple(float_scores)


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
                'pkill -f pantheon ; pkill -f iperf ; pkill -f mm-link ; '
                'pkill -f mm-delay ; pkill -f mm-loss']
        sys.stderr.write('+ %s\n' % ' '.join(cmd))
        setup_procs.append(Popen(cmd))

    for proc in setup_procs:
        proc.wait()


def run_experiment(args):
    if args['pkill']:
        clean_up_processes(args)

    run_proxy = '~/replication_with_emulation/run_proxy.py'

    params = []
    params += ['--bandwidth', ','.join(map(str, args['bandwidth']))]
    params += ['--delay', ','.join(map(str, args['delay']))]
    params += ['--uplink-queue', ','.join(map(str, args['uplink_queue']))]
    params += ['--uplink-loss', ','.join(map(str, args['uplink_loss']))]
    params += ['--downlink-loss', ','.join(map(str, args['downlink_loss']))]

    logs_dir = path.join(local_replication_dir, 'candidate_results')
    create_empty_directory(logs_dir)

    for base_id in xrange(0, 1):
        ip_index = 0
        ip_dict = {}
        proxy_procs = []
        for run_id in xrange(base_id * 5 + 1, base_id * 5 + 6):
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

        copy_logs(args, ip_dict, logs_dir)

    create_metadata_file(args, logs_dir)
    scores = replication_score(args, logs_dir)

    search_log = open(path.join(local_replication_dir, 'brazil_entropy_search_log'),
                      'a', 0)
    search_log.write(serialize(args, scores))
    search_log.close()

    '''
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
    '''

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

        cmd = ssh_cmd + ['cd ~/replication_with_emulation && git pull']
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


def get_args():
    args = {}
    args['ips'] = '54.201.130.161 54.203.15.127 54.201.51.117 54.149.193.222 54.218.53.148 54.212.220.122 54.202.95.26 54.218.61.216 54.202.229.253 54.202.170.179 54.149.80.130 54.149.211.10 54.202.93.105 54.200.53.132 54.186.211.200 54.186.102.25 54.202.92.83 54.201.3.241 54.202.101.54 54.200.55.46 54.201.210.38 54.149.63.197 54.200.110.30 54.202.87.202 54.202.87.143 54.201.85.73 54.202.113.39 54.202.202.255 54.214.109.106 54.214.101.228 54.187.188.204 54.202.209.75 54.202.121.129 54.213.59.239 54.200.250.243 54.202.81.183 54.214.75.73 54.214.73.9 54.149.60.158 54.202.201.70 54.214.99.226 54.213.95.126 54.214.79.235 54.202.113.238 54.200.190.99'
    args['ips'] = args['ips'].split()

    args['max_iters'] = 1
    args['replicate'] = '2017-01-04T07-24-AWS-Brazil-1-to-Brazil-10-runs-logs'
    args['location'] = 'brazil_entropy_'

    args['schemes'] = ['default_tcp', 'vegas', 'ledbat', 'pcc', 'verus',
                       'scream', 'sprout', 'webrtc', 'quic']
    '''
    args['best_tput_median_score'] = get_best_score(
            args, 'best_tput_median_score')
    args['best_delay_median_score'] = get_best_score(
            args, 'best_delay_median_score')
    '''
    args['best_overall_median_score'] = get_best_score(
            args, 'best_overall_median_score')

    args['pkill'] = True
    #setup_replication(args)
    #setup_pantheon(args)

    return args


def main(job_id, params):
    args = get_args()

    unit_vars = []
    unit_vars.append(params['bandwidth'][0])
    unit_vars.append(params['delay'][0])
    unit_vars.append(params['uplink_queue'][0])
    unit_vars.append(params['uplink_loss'][0])
    unit_vars.append(params['downlink_loss'][0])

    bounds = []
    bounds.append((35.59, 195.26))
    bounds.append((0, 5))
    bounds.append((10, 1710))
    bounds.append((0, 0.1))
    bounds.append((0, 0.1))

    entropy = 0.0
    real_x = []
    for i in xrange(0, 5):
        unit_x = float(unit_vars[i])
        (min_x, max_x) = bounds[i]

        eps = pow(2, -15)
        if unit_x > 1 - eps:
            unit_x = 1 - eps
        elif i <= 2 and unit_x < eps:
            unit_x = eps

        if unit_x > 1.0 - 1.0 / 32.0:
            entropy += -10 * (5 + math.log(1 - unit_x, 2))
        elif i <= 2 and unit_x < 1.0 / 32.0:
            entropy += -10 * (5 + math.log(unit_x, 2))

        if i <= 2:
            x = unit_x * (max_x - min_x) + min_x
        else:
            c = math.log(max_x * pow(10, 4) + 1, 10)
            x = pow(10, -4) * ((pow(10, c * unit_x)) - 1)

        real_x.append(x)

    args['bandwidth'] = (real_x[0], 0)
    args['delay'] = (int(math.ceil(real_x[1])), 0)
    args['uplink_queue'] = (int(math.ceil(real_x[2])), 0)
    args['uplink_loss'] = (real_x[3], 0)
    args['downlink_loss'] = (real_x[4], 0)

    scores = run_experiment(args)

    ret = scores[2] + entropy
    return ret
