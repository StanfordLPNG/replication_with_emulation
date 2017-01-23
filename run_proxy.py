#!/usr/bin/env python

import os
import sys
import random
import argparse
from subprocess import check_call
from os import path

pantheon = path.expanduser('~/pantheon')
test_dir = path.join(pantheon, 'test')
replication_dir = path.abspath(path.dirname(__file__))


def run_test(args):
    test_src = path.join(test_dir, 'test.py')

    params = []
    params += ['--uplink-trace', args['uplink_trace']]
    params += ['--downlink-trace', args['downlink_trace']]

    extra_cmd = 'mm-delay %d' % args['delay']
    if args['uplink_loss']:
        extra_cmd += ' mm-loss uplink %.4f' % args['uplink_loss']
    if args['downlink_loss']:
        extra_cmd += ' mm-loss downlink %.4f' % args['downlink_loss']

    if args['append']:
        params += ['--append-mm-cmds', extra_cmd]
    else:
        params += ['--prepend-mm-cmds', extra_cmd]

    params += ['--extra-mm-link-args', '--uplink-queue=droptail '
               '--uplink-queue-args=packets=%d' % args['uplink_queue']]
    params += ['--run-id', str(args['run_id']), args['cc']]

    cmd = ['python', test_src] + params
    sys.stderr.write('+ %s\n' % ' '.join(cmd))

    try:
        check_call(cmd)
    except:
        sys.stderr.write('Error: %s run %d\n' % (args['cc'], args['run_id']))


def gen_trace(bw):
    traces_dir = path.join(replication_dir, 'traces')
    try:
        os.makedirs(traces_dir)
    except:
        pass

    gen_trace_path = path.join(replication_dir, 'gen_const_bandwidth_trace.py')
    bw = '%.2f' % bw
    cmd = ['python', gen_trace_path, bw]
    sys.stderr.write('+ %s\n' % ' '.join(cmd))
    check_call(cmd, cwd=traces_dir)
    return path.join(traces_dir, bw + 'mbps.trace')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id',
                        metavar='min_id,max_id', required=True)
    parser.add_argument('--bandwidth',
                        metavar='mean,stddev', required=True)
    parser.add_argument('--delay',
                        metavar='mean,stddev', required=True)
    parser.add_argument('--uplink-queue', action='store', dest='uplink_queue',
                        metavar='mean,stddev', required=True)
    parser.add_argument('--uplink-loss', action='store', dest='uplink_loss',
                        metavar='mean,stddev', required=True)
    parser.add_argument(
            '--downlink-loss', action='store', dest='downlink_loss',
            metavar='mean,stddev', required=True)
    parser.add_argument(
            '--append', action='store_true', default=False)
    parser.add_argument('--schemes',
                        metavar='scheme1,scheme2,...', required=True)
    prog_args = parser.parse_args()

    min_run_id, max_run_id = map(int, prog_args.run_id.split(','))
    bw_mean, bw_stddev = map(float, prog_args.bandwidth.split(','))
    delay_mean, delay_stddev = map(float, prog_args.delay.split(','))
    queue_mean, queue_stddev = map(float, prog_args.uplink_queue.split(','))
    uploss_mean, uploss_stddev = map(float, prog_args.uplink_loss.split(','))
    downloss_mean, downloss_stddev = map(
            float, prog_args.downlink_loss.split(','))
    cc_schemes = prog_args.schemes.split(',')

    # default mahimahi parameters
    args = {}
    args['append'] = prog_args.append

    for run_id in xrange(min_run_id, max_run_id + 1):
        args['run_id'] = run_id

        bw = max(0, random.gauss(bw_mean, bw_stddev))
        trace_path = gen_trace(bw)
        args['uplink_trace'] = trace_path
        args['downlink_trace'] = trace_path

        args['delay'] = max(
                0, int(round(random.gauss(delay_mean, delay_stddev))))
        args['uplink_queue'] = max(
                0, int(round(random.gauss(queue_mean, queue_stddev))))
        args['uplink_loss'] = min(1, max(
                0, random.gauss(uploss_mean, uploss_stddev)))
        args['downlink_loss'] = min(1, max(
                0, random.gauss(downloss_mean, downloss_stddev)))

        for cc in cc_schemes:
            args['cc'] = cc
            run_test(args)


if __name__ == '__main__':
    main()
