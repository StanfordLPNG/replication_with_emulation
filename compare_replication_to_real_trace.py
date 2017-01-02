#!/usr/bin/env python

import argparse
import subprocess
import os
from tabulate import tabulate


def get_stats(tunnel_graph_path, filename):
    proc = subprocess.Popen([tunnel_graph_path, '500', filename],
                            stderr=subprocess.PIPE)
    _, output = proc.communicate()
    throughput_line = output.splitlines()[1].split()
    assert throughput_line[-1] == 'Mbit/s'
    throughput = float(throughput_line[-2])

    delay_line = output.splitlines()[2].split()
    assert delay_line[-1] == 'ms'
    delay = float(delay_line[-2])
    return (throughput, delay)


def get_difference(metric_1, metric_2):
    return '%.1f' % ((100. * abs(metric_1 - metric_2)) / metric_1)


parser = argparse.ArgumentParser()

parser.add_argument('scheme_name',
                    help='Name of congestion control scheme run')
parser.add_argument('log_1',
                    help='Log file from a pantheon run')
parser.add_argument('log_1_name',
                    help='Name for log file 1')
parser.add_argument('log_2',
                    help='Log file from a pantheon run')
parser.add_argument('log_2_name',
                    help='Name for log file 2')

parser.add_argument('--pantheon-dir', default="~/pantheon",
                    help='path of pantheon repository (default is ~/pantheon)')

args = parser.parse_args()

tunnel_graph_path = os.path.expanduser(os.path.join(args.pantheon_dir,
                                                    'analyze/tunnel_graph.py'))

output = []
(real_throughput, real_delay) = get_stats(tunnel_graph_path, args.log_1)
(emu_throughput, emu_delay) = get_stats(tunnel_graph_path, args.log_2)

output.append([args.scheme_name, 'throughput (Mbit/s)', real_throughput,
               emu_throughput,
               get_difference(real_throughput, emu_throughput)])
output.append([args.scheme_name, 'delay (ms)', real_delay, emu_delay,
               get_difference(real_delay, emu_delay)])

output_headers = ['scheme', 'metric', args.log_1_name, args.log_2_name,
                  'difference %']

print tabulate(output, headers=output_headers)
