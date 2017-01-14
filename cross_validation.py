#!/usr/bin/env python

import os
import sys
import time
import json
import shutil
import argparse
from subprocess import Popen, check_output, check_call
from os import path
from bayes_opt import BayesianOptimization
import proxy_master
# loop through all of the schemes
# report a nice table of cross validation scores

def gain_function(bandwidth, delay, uplink_queue, uplink_loss, downlink_loss):
    global args
    args['bandwidth'] = (bandwidth, 0)
    args['delay'] = (delay, 0)
    args['uplink_queue'] = (uplink_queue, 0)
    args['uplink_loss'] = (uplink_loss, 0)
    args['downlink_loss'] = (downlink_loss, 0)

    [tput_median_score, delay_median_score, best_overall_median_score] = proxy_master.run_experiment(args)
    return 500.0 - (best_overall_median_score)

def run_bayes():
    global args
    bounds = {
            "bandwidth": (80, 110),
            "delay": (10, 30),
            "uplink_queue":(0,3000),
            "uplink_loss": (0, .03),
            "downlink_loss":(0, .03)}
    bo = BayesianOptimization( gain_function, bounds)
    bo.maximize(init_points=5, n_iter=args['max_iters'])
    best_params = bo.res['max']['max_params']
    best_value = 500 - bos.res['max']['max_val']
    print "The best score on training on 8 of the schemes is {} provided by {}".format(best_value, best_params)
    return best_value, best_params

def add_params_to_args(params, args):
    for key in ["bandwidth", "delay", "uplink_queue", "uplink_loss", "downlink_loss"]:
        args[key] = (params[key],0)
    return args

def main():
    global args
    args = {}
    proxy_master.get_args(args)
    default_schemes = ['default_tcp', 'vegas', 'ledbat', 'pcc', 'verus',
                       'scream', 'sprout', 'webrtc', 'quic']
    scheme_to_test = "vegas"
    if scheme_to_test not in default_schemes:
        exit("Please provide a valid scheme for cross validation. Choices are {}".format(default_schemes))

    training_schemes = [scheme for scheme in default_schemes if scheme != scheme_to_test]
    # replace the schemes
    args['schemes'] = training_schemes
    print args
    # run bayesian optimization on everything but the one scheme
    score, params = run_bayes()

    # run the experiment on the scheme that was knocked out
    copy_args = args
    copy_args["schemes"] = [scheme_to_test]
    add_params_to_args(params, copy_args)
    median_throughput, median_delay = proxy_master.run_experiment(copy_args)
    avg = (median_throughput + median_delay)/2
    print "The median throughput and the median delay with the last scheme, {}, is {} and {}; the constest score is {}".format(scheme_to_test, median_throughput, median_delay, avg)

if __name__ == '__main__':
    main()


