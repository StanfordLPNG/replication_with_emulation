#!/usr/bin/env python

import sys
import collections
import random
import argparse
from os import path
sys.path.append(path.abspath(path.dirname(__file__)))
from on_off_interval import get_on_off_interval
from arrivals_per_ms import get_arrivals_per_ms


def weighted_pick(d):
    r = random.uniform(0, sum(d.itervalues()))
    s = 0.0

    for k, w in d.iteritems():
        s += w
        if r < s:
            return k

    return k


def main(log_path):
    # calculate Marcov MLE of transition matrix
    on_off_interval = get_on_off_interval(log_path)

    states = [0, 0]  # off, on
    trans = [[0, 0], [0, 0]]

    for interval in on_off_interval:
        states[0] += interval - 1
        states[1] += 1

        if interval == 1:
            trans[1][1] += 1
        else:
            trans[0][1] += 1
            trans[1][0] += 1
            trans[0][0] += interval - 2

    trans_prob = [[0, 0], [0, 0]]

    for s in [0, 1]:
        for t in [0, 1]:
            trans_prob[s][t] = float(trans[s][t]) / float(states[s])

    # empirical emission probability distribution
    arrivals_per_ms = get_arrivals_per_ms(log_path)
    emission_cnt = collections.Counter(arrivals_per_ms)

    # generate trace
    for i in xrange(1, 11):
        trace = open('on_off_trace_%s' % i, 'w')

        curr_s = 0 if random.random() < 0.5 else 1
        oppo_s = 1 - curr_s

        for ts in xrange(0, 60000):
            if random.random() < trans_prob[curr_s][oppo_s]:
                curr_s = oppo_s
                oppo_s = 1 - curr_s

            if curr_s == 1:
                pkts = weighted_pick(emission_cnt)
                for _ in xrange(pkts):
                    trace.write('%s\n' % ts)

        trace.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('log_path', metavar='LOG-PATH')
    args = parser.parse_args()

    main(args.log_path)
