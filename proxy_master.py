#!/usr/bin/env python

import os
import sys
import time
import json
import shutil
import argparse
from subprocess import Popen, check_output, check_call
from os import path

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
    metadata['run_times'] = args['runs']

    metadata_path = path.join(logs_dir, 'pantheon_metadata.json')
    with open(metadata_path, 'w') as metadata_file:
        json.dump(metadata, metadata_file)


def get_comparison_score(logs_dir):
    compare_src = path.join(local_analyze_dir, 'compare_two_experiments.py')
    nepal_logs = path.join(local_replication_dir,
                           '2017-01-03T21-30-Nepal-to-AWS-India-10-runs-logs')
    cmd = ['python', compare_src, nepal_logs, logs_dir]
    sys.stderr.write('+ %s\n' % ' '.join(cmd))
    results = check_output(cmd)

    result_path = path.join(logs_dir, 'comparison_result')
    with open(result_path, 'w') as result_file:
        result_file.write(results)

    scores = results.split('\n')
    median_score = float(scores[-4][:-1])
    stddev_score = float(scores[-2][:-1])

    sys.stderr.write('scores: %s %s\n' % (scores[-4], scores[-2]))
    return median_score, stddev_score


def save_best_results(logs_dir, dst_dir):
    try:
        shutil.rmtree(dst_dir)
    except:
        pass

    cmd = 'cp -r %s %s' % (logs_dir, dst_dir)
    check_call(cmd, shell=True)


def run_experiment(args):
    run_proxy = '~/replication_with_emulation/run_proxy.py'

    proxy_procs = []
    run_id_dict = {}
    min_run_id = 1

    params = []
    params += ['--bandwidth', ','.join(map(str, args['bandwidth']))]
    params += ['--delay', ','.join(map(str, args['delay']))]
    params += ['--schemes', ','.join(args['schemes'])]

    for ip in args['ips']:
        max_run_id = min_run_id + args['runs_per_ip'] - 1
        run_id_dict[ip] = (min_run_id, max_run_id)

        ssh_cmd = ['ssh', 'ubuntu@' + ip]
        cmd = ssh_cmd + ['python', run_proxy] + params
        cmd += ['--run-id', ','.join(map(str, run_id_dict[ip]))]

        sys.stderr.write('+ %s\n' % ' '.join(cmd))
        proxy_procs.append(Popen(cmd))

        min_run_id += args['runs_per_ip']

    for proc in proxy_procs:
        proc.wait()

    logs_dir = copy_logs(args, run_id_dict)
    create_metadata_file(args, logs_dir)
    median_score, stddev_score = get_comparison_score(logs_dir)

    if median_score < args['best_median_score']:
        args['best_median_score'] = median_score
        save_best_results(logs_dir, path.join(local_replication_dir,
                                              'best_median_results'))

    if stddev_score < args['best_stddev_score']:
        args['best_stddev_score'] = stddev_score
        save_best_results(logs_dir, path.join(local_replication_dir,
                                              'best_stddev_results'))

    return median_score, stddev_score


def setup(args):
    # kill all pantheon and iperf processes on proxies
    setup_procs = []
    for ip in args['ips']:
        ssh_cmd = ['ssh', 'ubuntu@' + ip]

        cmd = ssh_cmd + ['pkill -f pantheon']
        sys.stderr.write('+ %s\n' % ' '.join(cmd))

        cmd = ssh_cmd + ['pkill -f iperf']
        sys.stderr.write('+ %s\n' % ' '.join(cmd))
        setup_procs.append(Popen(cmd))

    for proc in setup_procs:
        proc.wait()

    # update git repos on proxies
    setup_procs = []
    for ip in args['ips']:
        ssh_cmd = ['ssh', 'ubuntu@' + ip]

        cmd = ssh_cmd + ['cd ~/replication_with_emulation && git pull']
        sys.stderr.write('+ %s\n' % ' '.join(cmd))
        setup_procs.append(Popen(cmd))

        cmd = ssh_cmd + ['cd ~/pantheon/test && ./run.py --run-only setup']
        sys.stderr.write('+ %s\n' % ' '.join(cmd))
        setup_procs.append(Popen(cmd))

    for proc in setup_procs:
        proc.wait()


def serialize(args, median_score, stddev_score):
    return ('bandwidth=[%s],delay=[%s],median_score=%s,stddev_score=%s\n' % (
            ','.join(map(str, args['bandwidth'])),
            ','.join(map(str, args['delay'])),
            median_score, stddev_score))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'ips', metavar='IP', nargs='+', help='proxy\'s IP address')
    parser.add_argument(
        '--max-iters', metavar='N', action='store', dest='max_iters',
        type=int, default=1, help='max iterations (default 1)')
    parser.add_argument('--include-setup', action='store_true', dest='setup')
    prog_args = parser.parse_args()

    args = {}
    args['ips'] = prog_args.ips
    args['runs'] = 10
    args['max_iters'] = prog_args.max_iters

    if args['runs'] % len(args['ips']) != 0:
        sys.stderr.write('The number of proxy should be a factor of %s\n'
                         % args['runs'])
        exit(1)

    args['runs_per_ip'] = args['runs'] / len(args['ips'])
    args['schemes'] = ['default_tcp', 'vegas', 'ledbat', 'pcc', 'verus',
                       'scream', 'sprout', 'webrtc', 'quic']
    args['best_median_score'] = sys.maxint
    args['best_stddev_score'] = sys.maxint

    if prog_args.setup:
        setup(args)

    search_log = open('search_log', 'a')

    for bw in [(8.5, 10.5)]:
        for delay in [(27, 29)]:
            args['bandwidth'] = bw
            args['delay'] = delay
            median_score, stddev_score = run_experiment(args)

            search_log.write(serialize(args, median_score, stddev_score))

    search_log.close()
    sys.stderr.write('Best scores: %s%% %s%%\n' %
                     (args['best_median_score'], args['best_stddev_score']))


if __name__ == '__main__':
    main()