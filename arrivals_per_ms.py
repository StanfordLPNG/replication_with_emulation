#!/usr/bin/env python

import argparse
import collections


def get_arrivals_per_ms(log_path):
    # get arrivals per ms
    arrivals_per_ms = []
    pkts = 0

    log = open(log_path)

    last_ts = None
    for line in log:
        items = line.split()
        if len(items) < 4 or items[1] != '-':
            continue

        ts = int(items[0])

        if ts != last_ts:
            if last_ts != None:
                arrivals_per_ms.append(pkts)
            pkts = 1
        else:
            pkts += 1

        last_ts = ts

    log.close()

    return arrivals_per_ms


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('log_path', metavar='LOG-PATH')
    args = parser.parse_args()

    data = get_arrivals_per_ms(args.log_path)
    data_cnt = collections.Counter(data)

    print 'Arrivals per ms: (arrivals_per_ms, occurrence)'
    print sorted(data_cnt.items(), key=lambda x: x[0])
