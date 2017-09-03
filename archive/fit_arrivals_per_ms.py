#!/usr/bin/env python

import sys
from os import path
sys.path.append(path.abspath(path.dirname(__file__)))
import argparse
from arrivals_per_ms import get_arrivals_per_ms
from find_best_fit import find_best_fit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('log_path', metavar='LOG-PATH')
    args = parser.parse_args()

    data = get_arrivals_per_ms(args.log_path)
    find_best_fit(data)


if __name__ == '__main__':
    main()
