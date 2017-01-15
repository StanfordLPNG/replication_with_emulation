#!/usr/bin/env python

import os
import sys
import time
import json
import shutil
import argparse
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


def copy_logs(args, run_id_dict):
    logs_dir = path.join(local_replication_dir, 'candidate_results')
    create_empty_directory(logs_dir)

    copy_procs = []
    for ip in args['ips']:
        run_ids = range(run_id_dict[ip][0], run_id_dict[ip][1] + 1)

        if len(args['schemes']) > 1:
            schemes_name = '{%s}' % ','.join(args['schemes'])
        else:
            schemes_name = args['schemes'][0]

        if len(run_ids) > 1:
            run_name = '{%s}' % ','.join(map(str, run_ids))
        else:
            run_name = '%s' % run_ids[0]

        logs_to_copy = '%s*run%s.log' % (schemes_name, run_name)
        logs_to_copy = '%s:~/pantheon/test/%s' % (ip, logs_to_copy)
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
    metadata['run_times'] = args['runs']

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
    return ('bandwidth=[%s],delay=[%s],uplink_queue=[%s],uplink_loss=[%s],'
            'downlink_loss=[%s],tput_median_score=%s,delay_median_score=%s,'
            'overall_median_score=%s\n'
            % (','.join(map(str, args['bandwidth'])),
               ','.join(map(str, args['delay'])),
               ','.join(map(str, args['uplink_queue'])),
               ','.join(map(str, args['uplink_loss'])),
               ','.join(map(str, args['downlink_loss'])),
               scores[0], scores[1], scores[2]))


def clean_up_processes(args):
    # kill all pantheon and iperf processes on proxies
    setup_procs = []
    for ip in args['ips']:
        ssh_cmd = ['ssh', ip]

        cmd = ssh_cmd + [
                'pkill -f pantheon && pkill -f iperf && pkill -f mm-link && '
                'pkill -f mm-delay && pkill -f mm-loss']
        sys.stderr.write('+ %s\n' % ' '.join(cmd))
        setup_procs.append(Popen(cmd))

    for proc in setup_procs:
        proc.wait()


def run_experiment(args):
    if args['pkill']:
        clean_up_processes(args)

    run_proxy = '~/replication_with_emulation/run_proxy.py'

    proxy_procs = []
    run_id_dict = {}
    min_run_id = 1

    params = []
    params += ['--bandwidth', ','.join(map(str, args['bandwidth']))]
    params += ['--delay', ','.join(map(str, args['delay']))]
    params += ['--uplink-queue', ','.join(map(str, args['uplink_queue']))]
    params += ['--uplink-loss', ','.join(map(str, args['uplink_loss']))]
    params += ['--downlink-loss', ','.join(map(str, args['downlink_loss']))]
    params += ['--schemes', ','.join(args['schemes'])]

    for ip in args['ips']:
        max_run_id = min_run_id + args['runs_per_ip'] - 1
        run_id_dict[ip] = (min_run_id, max_run_id)

        ssh_cmd = ['ssh', ip]
        cmd = ssh_cmd + ['python', run_proxy] + params
        cmd += ['--run-id', ','.join(map(str, run_id_dict[ip]))]

        sys.stderr.write('+ %s\n' % ' '.join(cmd))
        proxy_procs.append(Popen(cmd))

        min_run_id += args['runs_per_ip']

    for proc in proxy_procs:
        proc.wait()

    logs_dir = copy_logs(args, run_id_dict)
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
        ssh_cmd = ['ssh', ip]

        cmd = ssh_cmd + ['cd ~/replication_with_emulation && git pull']
        sys.stderr.write('+ %s\n' % ' '.join(cmd))
        setup_procs.append(Popen(cmd))

    for proc in setup_procs:
        proc.wait()


def setup_pantheon(args):
    setup_procs = []
    for ip in args['ips']:
        ssh_cmd = ['ssh', ip]

        cmd = ssh_cmd + ['cd ~/pantheon/test && ./run.py --run-only setup']
        sys.stderr.write('+ %s\n' % ' '.join(cmd))
        setup_procs.append(Popen(cmd))

    for proc in setup_procs:
        proc.wait()


def get_args():
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
        '--experiments-per-ip', metavar='N', action='store',
        dest='experiments_per_ip', type=int, default=1,
        help='run all schemes n times on each machine (default 1)')
    parser.add_argument(
        '--location',
        help='location to replicate (used in saved file/folder names)')
    parser.add_argument(
        '--replicate', metavar='LOG-PATH', required=True,
        help='logs of real world experiment to replicate')
    prog_args = parser.parse_args()

    args = {}
    args['ips'] = prog_args.ips
    args['runs_per_ip'] = prog_args.experiments_per_ip
    args['runs'] = prog_args.experiments_per_ip * len(prog_args.ips)
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

    return args


def main():
    args = get_args()

    search_log = open(args['location'] + 'search_log', 'a', 0)
    args['search_log'] = search_log

    for i in xrange(args['max_iters']):
        args['delay'] = (100, 0)
        args['bandwidth'] = (3.0, 0)
        args['uplink_queue'] = (1000, 0)
        args['uplink_loss'] = (0.01, 0)
        args['downlink_loss'] = (0.01, 0)

        scores = run_experiment(args)

    search_log.close()
    sys.stderr.write('Best tput median score: %s%%\n' %
                     args['best_tput_median_score'])
    sys.stderr.write('Best delay median score: %s%%\n' %
                     args['best_delay_median_score'])
    sys.stderr.write('Best overall median score: %s%%\n' %
                     args['best_overall_median_score'])


if __name__ == '__main__':
    main()
