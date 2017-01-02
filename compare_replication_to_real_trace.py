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

parser = argparse.ArgumentParser()

parser.add_argument('scheme_name',
                    help='Name of congestion control scheme run')
parser.add_argument('real_log',
                    help='Log file from a real pantheon run')
parser.add_argument('emulated_log',
                    help='Log file from an emulated pantheon run')

parser.add_argument('--pantheon-dir', default="~/pantheon",
                    help='path of pantheon repository (default is ~/pantheon)')

args = parser.parse_args()

tunnel_graph_path = os.path.expanduser(os.path.join(args.pantheon_dir,
                                                    'analyze/tunnel_graph.py'))

output = []
(real_throughput, real_delay) = get_stats(tunnel_graph_path, args.real_log)
(emu_throughput, emu_delay) = get_stats(tunnel_graph_path, args.real_log)

output.append([args.scheme_name, 'throughput (Mbit/s)', real_throughput,
               emu_throughput,
               abs(real_throughput-emu_throughput)/real_throughput])
output.append([args.scheme_name, 'delay (ms)', real_delay, emu_delay,
               abs(real_delay-emu_delay)/real_delay])

output_headers = ['scheme', 'metric', 'real link', 'emulated link',
                  'difference %']

print tabulate(output, headers=output_headers)
