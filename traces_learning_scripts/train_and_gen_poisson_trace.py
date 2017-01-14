#!/usr/bin/env python

import sys
import random
import argparse
from os import path
sys.path.append(path.abspath(path.dirname(__file__)))
from interarrival_times import get_interarrival_times


def train_lambda(log_path):
    data = get_interarrival_times(log_path)
    return float(len(data) - 1) / sum(data)


def generate_trace(lambd):
    for run_id in xrange(1, 11):
        curr_ts = 0
        trace = open('poisson_trace_%s' % run_id, 'w')

        while curr_ts < 60000:
            curr_ts += int(round(random.expovariate(lambd)))
            trace.write('%s\n' % curr_ts)

        trace.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('log_path', metavar='LOG-PATH')
    args = parser.parse_args()

    lambd = train_lambda(args.log_path)
    print 'Poisson process lambda:', lambd
    generate_trace(lambd)


if __name__ == '__main__':
    main()
