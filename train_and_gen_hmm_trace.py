#!/usr/bin/env python

import argparse
import numpy as np
from hmmlearn import hmm


# get arrivals or silence per ms
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

                for silent_ts in xrange(last_ts + 1, ts):
                    arrivals_per_ms.append(0)

            pkts = 1
        else:
            pkts += 1

        last_ts = ts

    log.close()

    return arrivals_per_ms


def train_hmm(log_path):
    X = get_arrivals_per_ms(log_path)

    # add at least one value in case any value is missing
    for i in xrange(0, 27):
        X.append(i)

    # only allow output to be [0, 26]
    for i in xrange(len(X)):
        if X[i] > 26:
            X[i] = 26

    # initialize start probability and transition matrix
    n_states = 4
    p = 1.0 / n_states
    start_prob = np.ones(n_states) * p
    trans_mat = np.ones((n_states, n_states)) * p

    # initialize emission probability
    n_emissions = 27
    p = 1.0 / n_emissions
    emission_prob = np.ones((n_states, n_emissions)) * p

    # train HMM
    model = hmm.MultinomialHMM(n_components=n_states, n_iter=100)
    model.startprob_ = start_prob
    model.transmat_ = trans_mat
    model.emissionprob_ = emission_prob

    X = np.array([X])
    model.fit(X.T)

    return model


def generate_trace(model):
    for run_id in xrange(1, 11):
        X = model.sample(60000)[0]
        trace = open('hmm_trace_%s' % run_id, 'w')

        for ts in xrange(X.size):
            for i in xrange(X[ts][0]):
                trace.write('%s\n' % ts)

        trace.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('log_path', metavar='LOG-PATH')
    args = parser.parse_args()

    model = train_hmm(args.log_path)
    generate_trace(model)


if __name__ == '__main__':
    main()
