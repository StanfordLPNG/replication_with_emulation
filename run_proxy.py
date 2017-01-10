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

    pre_cmd = 'mm-delay %d' % args['delay']
    if args['uplink_loss']:
        pre_cmd += ' mm-loss uplink %.4f' % args['uplink_loss']
    if args['downlink_loss']:
        pre_cmd += ' mm-loss downlink %.4f' % args['downlink_loss']
    params += ['--prepend-mm-cmds', pre_cmd]

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
                        metavar='min_mbps,max_mbps', required=True)
    parser.add_argument('--delay',
                        metavar='min_ms,max_ms', required=True)
    parser.add_argument('--schemes',
                        metavar='scheme1,scheme2,...', required=True)
    prog_args = parser.parse_args()

    min_run_id, max_run_id = map(int, prog_args.run_id.split(','))
    min_bw, max_bw = map(float, prog_args.bandwidth.split(','))
    min_delay, max_delay = map(int, prog_args.delay.split(','))
    cc_schemes = prog_args.schemes.split(',')

    # default mahimahi parameters
    args = {}
    args['uplink_queue'] = 175
    args['uplink_loss'] = 0.004
    args['downlink_loss'] = 0.003

    for run_id in xrange(min_run_id, max_run_id + 1):
        args['run_id'] = run_id

        bw = random.uniform(min_bw, max_bw)
        trace_path = gen_trace(bw)
        args['uplink_trace'] = trace_path
        args['downlink_trace'] = trace_path

        args['delay'] = random.randint(min_delay, max_delay)
        for cc in cc_schemes:
            args['cc'] = cc
            run_test(args)


if __name__ == '__main__':
    main()
