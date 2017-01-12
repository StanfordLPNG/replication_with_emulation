#!/usr/bin/env python

import os
import sys
import time
import json
import shutil
import argparse
from subprocess import Popen, check_output, check_call
from os import path
import math
import numpy as np
from random import uniform
import proxy_master
import random as random
#import test
"""
File that implement spsa, gradient descent for multiple variables,
to search for best pantheon run parameters
"""

# Algorithm to implement spsa
# theta -> initial parameters - numpy array
# A, alpha, gamma -> constants
# k -> number of iterations of spsa
# delta -> how to adjust each parameter in theta
# returns theta, represents the
def spsa(y, theta, a, A, alpha, c, gamma, k, delta, args):
    print theta, delta
    if theta.size != delta.size:
        return " The length of the theta and delta array are not the same. Cannot perform spsa"
    for i in xrange(k):
        print "LOOPING"
        ak = a / math.pow((A + k + 1), alpha)
        ck = c / math.pow((k + 1 ), gamma)
        print ak, ck
        theta_plus = np.add(theta, delta)
        theta_minus = np.add(theta, delta)

        args_plus = un_normalize_theta(theta_plus, args)
        args_minus = un_normalize_theta(theta_minus, args)

        tput_median_plus, delay_median_plus= y(args_plus)
        tput_median_minus, delay_median_minus = y(args_minus)

        gk = [( (tput_median_plus/100 + delay_median_plus/100 )/2 - (tput_median_minus/100 + delay_median_minus/100 )/2 ) / ( 2 * ck * dk ) for dk in delta]
        for i in range(len(theta)):
            theta[i] = theta[i] - ak*gk[i]
        theta = constrain_theta(theta)
        print "CURRENT THETA #####"
        print theta, get_real_theta(theta)
        print gk
        print "CURRENT THETA$####"
    return theta

def gen_delta(p):
    delta = np.zeros(p)
    for i in xrange(p):
        delta[i] = random.choice([-1, 1])
    return delta

def get_real_theta(theta):
    theta = constrain_theta(theta)
    # makes the parameters real values
    #args_lo = np.array([2, 100, 500, 0, 0])
    #args_hi = np.array([6, 200, 2500, 0.02, 0.02])
    args_lo = np.array([9, 28, 50, .001, .001])
    args_hi = np.array([10, 30, 200, 0.009, 0.009])
    real_theta = np.multiply(theta, args_hi - args_lo) + args_lo
    return real_theta

def un_normalize_theta(theta, args):
    real_theta = get_real_theta(theta)
    args['bandwidth'] = (real_theta[0], 0)
    args['delay'] = (real_theta[1], 0)
    args['uplink_queue'] = (real_theta[2], 0)
    args['uplink_loss'] = (real_theta[3], 0)
    args['downlink_loss'] = (real_theta[4], 0)
    return args

def constrain_theta(theta):
    for i in xrange(len(theta)):
        theta[i] = min(1.0, max(0.0, theta[i]))
    return theta

def fake_function(a):
    return random.uniform(.20, .05), random.uniform(.16, .05)
def main():
    # run spsa for practice before involving the actal proxy master
    # need ( median, stddev) for delay, bandwidth, uplink queue
    # TODO: COME UP WITH BETTER CONSTANTS
    args = proxy_master.get_args() # same arguments from proxy master

    a = 2
    c =.6
    A = 5
    alpha = .602
    gamma = .404
    k = 5
    theta = np.array([0.5, 0.5, 0.5, 0.5, 0.5])
    delta = gen_delta(5)
    np.set_printoptions(precision=3, suppress=True)
    #theta = spsa( fake_function, theta, a, A, alpha, c, gamma, k, delta, args)
    theta = spsa( proxy_master.run_experiment, theta, a, A, alpha, c, gamma, k, delta, args)
    print theta
    print get_real_theta(theta)
    real_args = un_normalize_theta(theta, args)
    throughput, delay = proxy_master.run_experiment(real_args)
    print "REAL RESULTS ARE {} and {}".format(throughput, delay)
if __name__ == '__main__':
    main()

