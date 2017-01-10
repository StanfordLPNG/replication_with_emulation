#!/usr/bin/env python

import os
import sys
import random
import argparse
from subprocess import check_call
from os import path

pantheon = path.expanduser('~/pantheon')
test_dir = path.join(pantheon, 'test')
analyze_dir = path.join(pantheon, 'analyze')
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
        sys.stderr.write('Error: %s run %d\n' % (args['run_id'], args['cc']))


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
    parser.add_argument('min_run_id')
    parser.add_argument('max_run_id')
    prog_args = parser.parse_args()

    min_run_id = int(prog_args.min_run_id)
    max_run_id = int(prog_args.max_run_id)

    cc_schemes = ['default_tcp', 'vegas', 'ledbat', 'pcc', 'verus',
                  'scream', 'sprout', 'webrtc', 'quic']

    # default mahimahi parameters
    args = {}
    args['uplink_trace'] = path.join(test_dir, '9.6mbps.trace')
    args['downlink_trace'] = path.join(test_dir, '9.6mbps.trace')
    args['delay'] = 28
    args['uplink_queue'] = 175
    args['uplink_loss'] = 0.004
    args['downlink_loss'] = 0.003

    for run_id in xrange(min_run_id, max_run_id + 1):
        bw = random.uniform(9, 10)
        trace_path = gen_trace(bw)
        args['uplink_trace'] = trace_path

        bw = random.uniform(7, 9)
        trace_path = gen_trace(bw)
        args['downlink_trace'] = trace_path

        args['delay'] = random.randint(26, 30)
        args['uplink_queue'] = random.randint(160, 190)
        args['uplink_loss'] = random.uniform(0.002, 0.006)
        args['downlink_loss'] = random.uniform(0.001, 0.005)

        args['run_id'] = run_id
        for cc in cc_schemes:
            args['cc'] = cc
            run_test(args)


if __name__ == '__main__':
    main()
