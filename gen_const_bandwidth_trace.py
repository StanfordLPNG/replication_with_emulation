#!/usr/bin/env python

import argparse
import numpy as np

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('bandwidth', metavar='bandwidth_Mbps', type=float)
    args = parser.parse_args()

    pkts_per_sec = int(round(args.bandwidth * 250 / 3))
    pretty_bw = ('%f' % args.bandwidth).rstrip('0').rstrip('.')
    trace = open(pretty_bw + 'mbps.trace', 'w')

    for sec in xrange(0, 60):
        ts_list = np.random.uniform(sec * 1000, (sec + 1) * 1000, pkts_per_sec)
        ts_list = sorted(map(int, ts_list))

        for ts in ts_list:
            trace.write('%s\n' % ts)

    trace.close()


if __name__ == '__main__':
    main()
