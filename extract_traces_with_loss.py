#!/usr/bin/env python

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
            trace = open(trace_path, 'w')

            queue = deque()
            first_ts = None
            for line in log:
                if line.startswith('#'):
                    continue

                items = line.split()
                ts = float(items[0])

                if items[1] == '+':
                    queue.append(ts)
                elif items[1] == '-':
                    if first_ts is None:
                        first_ts = int(ts) - 1

                    delay = float(items[3])
                    while True:
                        queue_head = queue.popleft()
                        sent_ts = ts - delay
                        if abs(sent_ts - queue_head) <= 0.002:
                            trace.write('%s\n' % (int(ts) - first_ts))
                            break
                        elif sent_ts > queue_head:
                            trace.write('%s x\n' % (int(ts) - first_ts))
                        else:
                            sys.stderr.write('Cannot find sent packet for %s'
                                             % line)
                            exit(1)

            log.close()
            trace.close()


if __name__ == '__main__':
    main()
