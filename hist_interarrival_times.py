#!/usr/bin/env python

import sys
import argparse
from os import path
sys.path.append(path.abspath(path.dirname(__file__)))
from interarrival_times import get_interarrival_times

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('log_path', metavar='LOG-PATH')
    args = parser.parse_args()

    data = get_interarrival_times(args.log_path)

    fig, ax = plt.subplots()

    bins_num = max(data) - min(data)
    if bins_num > 50:
        bins_num = 50
    ax.hist(data, bins=bins_num, normed=True)
    ax.set_xlabel('Interarrival times (ms)')
    ax.set_ylabel('Frequency')
    ax.grid()

    fig.savefig('hist_interarrival_times.png', dpi=300,
                bbox_inches='tight', pad_inches=0.2)


if __name__ == '__main__':
    main()
