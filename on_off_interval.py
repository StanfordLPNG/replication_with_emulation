#!/usr/bin/env python

import sys
import collections
from os import path


def get_on_off_interval(log_path):
    # get on off interval
    on_off_interval = []

    log = open(log_path)

    last_ts = None
    for line in log:
        items = line.split()
        if len(items) < 4 or items[1] != '-':
            continue

        ts = int(items[0])

        if last_ts != None and ts != last_ts:
            on_off_interval.append(ts - last_ts)

        last_ts = ts

    log.close()

    return on_off_interval


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('log_path', metavar='LOG-PATH')
    args = parser.parse_args()

    data = get_on_off_interval(args.log_path)
    data_cnt = collections.Counter(data)

    print 'Interval between two ON states (ms): (interval, occurrence)'
    print sorted(data_cnt.items(), key=lambda x: x[0])
