#!/usr/bin/env python

import argparse
import numpy as np

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('bandwidth', metavar='bandwidth_mbps')
    args = parser.parse_args()

    pkts_per_sec = int(round(float(args.bandwidth) * 250 / 3))
    trace = open(args.bandwidth + 'mbps.trace', 'w')

    for sec in xrange(0, 60):
        ts_list = np.random.uniform(sec * 1000, (sec + 1) * 1000, pkts_per_sec)
        ts_list = sorted(map(int, ts_list))

        for ts in ts_list:
            trace.write('%s\n' % ts)

    trace.close()


if __name__ == '__main__':
    main()
