#!/usr/bin/env python

import sys
import collections
from os import path


def get_interarrival_times(log_path):
    # get interarrival times
    interarrival_times = []

    log = open(log_path)

    last_ts = None
    for line in log:
        items = line.split()
        if len(items) < 4 or items[1] != '-':
            continue

        ts = int(items[0])

        if last_ts != None:
            interarrival_times.append(ts - last_ts)

        last_ts = ts

    log.close()

    return interarrival_times


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('log_path', metavar='LOG-PATH')
    args = parser.parse_args()

    data = get_interarrival_times(args.log_path)
    data_cnt = collections.Counter(data)

    print 'Interarrival times (ms): (interarrival_times, occurrence)'
    print sorted(data_cnt.items(), key=lambda x: x[0])
