#!/usr/bin/env python

import sys
import os


def main():
    if len(sys.argv) != 2:
        sys.stderr.write('Usage: %s TRACE\n' % sys.argv[0])
        exit(1)

    trace_path = sys.argv[1]

    # read the last line of trace assuming it does not exceed 10 characters
    with open(trace_path, 'rb') as trace:
        first_ts = int(trace.readline())
        trace.seek(-10, os.SEEK_END)
        last_ts = int(trace.readlines()[-1])

    trace = open(trace_path)

    base_ts = 0
    for run_id in xrange(1, 11):
        new_trace = open('trace_%s' % run_id, 'w')

        if run_id < 10:
            next_partition = first_ts + run_id * (last_ts - first_ts) / 10.0
        else:
            next_partition = last_ts + 1

        curr_ts = None
        while True:
            line = trace.readline()
            if not line:
                exit(0)

            curr_ts = int(line)
            new_trace.write('%s\n' % (curr_ts - base_ts))

            if curr_ts >= next_partition:
                base_ts = curr_ts
                break

        new_trace.close()

    trace.close()


if __name__ == '__main__':
    main()
