#!/usr/bin/env python

import os
import sys
import time
import json
import shutil
import argparse
from subprocess import Popen, check_output
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


def save_best_results(logs_dir):
    best_results_dir = path.join(local_replication_dir, 'best_results')

    try:
        shutil.rmtree(best_results_dir)
    except:
        pass

    os.rename(logs_dir, best_results_dir)


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

    if median_score < 25 and stddev_score < 25:
        save_best_results(logs_dir)
        sys.stderr.write('Congratulations!\n')
        exit(0)

    return median_score, stddev_score


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('ips', metavar='IP', nargs='+',
                        help='proxy\'s IP address')
    parser.add_argument(
        '--max-iters', metavar='N', action='store', dest='max_iters',
        type=int, default=1, help='max iterations (default 10)')
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

    for i in xrange(args['max_iters']):
        args['bandwidth'] = [9, 10]
        args['delay'] = [26, 30]
        median_score, stddev_score = run_experiment(args)

    sys.stderr.write('Failed to find good results :(')


if __name__ == '__main__':
    main()
