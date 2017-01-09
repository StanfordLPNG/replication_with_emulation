#!/usr/bin/env python

import sys
import json
import argparse
from os import path
from collections import deque


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--data-dir',
        metavar='DIR',
        action='store',
        dest='data_dir',
        default='.',
        help='directory containing json and logs to extract real traces')
    args = parser.parse_args()
    data_dir = path.abspath(args.data_dir)

    # load pantheon_metadata.json as a dictionary
    metadata_fname = path.join(data_dir, 'pantheon_metadata.json')
    with open(metadata_fname) as metadata_file:
        metadata_dict = json.load(metadata_file)

    run_times = metadata_dict['run_times']
    cc_schemes = metadata_dict['cc_schemes'].split()

    for cc in cc_schemes:
        for run_id in xrange(1, 1 + run_times):
            log_path = path.join(args.data_dir,
                                 '%s_datalink_run%s.log' % (cc, run_id))
            trace_path = path.join(
                args.data_dir, '%s_datalink_run%s.loss.trace' % (cc, run_id))
            log = open(log_path)

            first_ts = None
            queue = []
            delivery = []
            for line in log:
                if line.startswith('#'):
                    continue

                items = line.split()
                ts = float(items[0])
                if first_ts is None:
                    first_ts = ts

                if items[1] == '+':
                    queue.append(ts)
                elif items[1] == '-':
                    delivery.append(ts)

                    delay = float(items[3])
                    sent_ts = ts - delay

                    i = 0
                    while True:
                        if i >= len(queue):
                            break

                        if abs(sent_ts - queue[i]) <= 0.005:
                            del queue[i]
                            break

                        i += 1

            log.close()

            trace = open(trace_path, 'w')
            for ts in xrange(1, int(first_ts)):
                trace.write('%s\n' % ts)

            p1 = 0 # queue
            p2 = 0 # delivery

            while p1 < len(queue) or p2 < len(delivery):
                if p1 < len(queue):
                    ts1 = queue[p1]
                else:
                    ts1 = None

                if p2 < len(delivery):
                    ts2 = delivery[p2]
                else:
                    ts2 = None

                if ts1 and ts2:
                    if ts1 < ts2:
                        trace.write('%s x\n' % int(round(ts1)))
                        p1 += 1
                    else:
                        trace.write('%s\n' % int(round(ts2)))
                        p2 += 1
                elif ts1:
                    trace.write('%s x\n' % int(round(ts1)))
                    p1 += 1
                elif ts2:
                    trace.write('%s\n' % int(round(ts2)))
                    p2 += 1

            trace.close()

if __name__ == '__main__':
    main()
