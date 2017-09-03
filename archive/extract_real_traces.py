#!/usr/bin/env python

import json
import argparse
from os import path


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
            trace_path = path.join(args.data_dir,
                                   '%s_datalink_run%s.trace' % (cc, run_id))
            log = open(log_path)
            trace = open(trace_path, 'w')

            first_ts = None
            for line in log:
                items = line.split()
                if items[1] == '-':
                    ts = int(round(float(items[0])))
                    if first_ts is None:
                        first_ts = ts - 1

                    trace.write('%s\n' % (ts - first_ts))

            log.close()
            trace.close()


if __name__ == '__main__':
    main()
