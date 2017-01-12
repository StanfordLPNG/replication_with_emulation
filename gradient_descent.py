#!/usr/bin/env python

import argparse
import math
import random
import numpy as np
from multiprocessing.pool import ThreadPool
from random import uniform
import proxy_master
#import test
"""
File that implement spsa, gradient descent for multiple variables,
to search for best pantheon run parameters
"""
def apply_min_or_max(a, b, minimum):
    if minimum:
        return min(a, b)
    else:
        return max(a, b)
def calculate_gradient(const, delta):
    return const/delta
# Algorithm to implement spsa
# theta -> initial parameters - numpy array
# A, alpha, gamma -> constants
# k -> number of iterations of spsa
# delta -> how to adjust each parameter in theta
# returns theta, represents the
def spsa(y, theta, a, A, alpha, c, gamma, k, delta, min_theta, max_theta, args):
    vfunc = np.vectorize(apply_min_or_max)
    vgrad_func = np.vectorize(calculate_gradient)
    if theta.size != delta.size or theta.size != min_theta.size or theta.size != max_theta.size:
        return " The length of the theta and delta array are not the same. Cannot perform spsa"

    if len(args['ips']) > 1:
        pool = ThreadPool(processes=2)
    else:
        pool = ThreadPool(processes=1)

    for i in xrange(k):
        ak = a / math.pow((A + k + 1), alpha)
        ck = c / math.pow((k + 1 ), gamma)

        theta_plus = np.add(theta, delta)
        theta_plus = vfunc(theta, max_theta, True)
        theta_minus = np.add(theta, delta)
        theta_minus = vfunc(theta, min_theta, False)
        args_plus = add_params_to_args(args, theta_plus)
        args_minus = add_params_to_args(args, theta_minus)

        if len(args['ips']) > 1:
            split_ips(args, args_plus, args_minus)

        plus_proc = pool.apply_async(y, (args_plus,))
        minus_proc = pool.apply_async(y, (args_minus,))

        tput_median_plus, delay_median_plus = plus_proc.get()
        tput_median_minus, delay_median_minus = minus_proc.get()

        gradient_constant = ( (tput_median_plus + delay_median_plus ) - (tput_median_minus + delay_median_minus ) ) / ( 2 * ck )
        gk = [gradient_constant/dk for dk in delta]
        for i in range(len(theta)):
            theta[i] = theta[i] - ak*gk[i]
        print theta
    return theta

def split_ips(original_args, args_1, args_2):
    ips = original_args['ips']
    random.shuffle(ips)
    args_1['ips'] = ips[::2]
    args_2['ips'] = ips[1::2]


def add_params_to_args(args, theta):
    # Takes the args from command line and adds the theta values from them
    args['delay'] = (theta[0], theta[1])
    args['bandwidth'] = (theta[2], theta[3])
    args['uplink_queue'] = (theta[4], theta[5])
    args['uplink_loss'] = (theta[6], theta[7])
    args['downlink_loss'] = (theta[8], theta[9])
    return args

def main():
    # run spsa for practice before involving the actal proxy master
    # need ( median, stddev) for delay, bandwidth, uplink queue
    # TODO: COME UP WITH BETTER CONSTANTS
    args = proxy_master.get_args() # same arguments from proxy master

    a = 5
    c = 2
    min_theta = np.array([15, 0, 6, 0, 50, 0, .002, 0, .002, 0])
    max_theta = np.array([40, 0, 12, 0, 200, 0, .006, 0, .006, 0])
    theta = np.array([28, 0, 9.6, 0, 175, 0, .004, 0, .003, 0])
    delta = np.array([2, 0, .4, 0, 20, 0, .0005, 0,0005, 0])
    A = .404
    alpha = .602
    gamma = .101
    k = 5
    theta = spsa( proxy_master.run_experiment, theta, a, A, alpha, c, gamma, k, delta, min_theta,max_theta, args)
    print theta

if __name__ == '__main__':
    main()

