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
"""
File that implement spsa, gradient descent for multiple variables,
to search for best pantheon run parameters
"""
def apply_min_or_max(a, b, minimum):
    if minimum:
        return min(a, b)
    else:
        return max(a, b)

# Algorithm to implement spsa
# theta -> initial parameters - numpy array
# A, alpha, gamma -> constants
# k -> number of iterations of spsa
# delta -> how to adjust each parameter in theta
# returns theta, represents the
def spsa(y, theta, a, A, alpha, c, gamma, k, delta, min_theta, max_theta):
    if theta.size != delta.size:
        return " The length of the theta and delta array are not the same. Cannot perform spsa"
    for i in xrange(k):
        ak = a / math.pow((A + k + 1), alpha)
        ck = c / math.pow((k + 1 ), gamma)

        theta_plus = np.add(theta, delta)
        theta_minus =np.add(theta, delta)

        y_plus = y(theta_plus)
        y_minus = y(theta_minus)

        gk = (y_plus - y_minus) / (2*ck)
        theta = theta - alpha * gk
        # make sure theta conforms to min and max values
        vfunc = np.vectorize(apply_min_or_max)
        theta = vfunc(theta, min_theta, False)
        theta = vfunc(theta, max_theta, True)
        print theta
    return theta

def run_proxy_master(theta):
    ret = uniform(15, 20)
    print "Returning value {} from proxy master".format(ret)
    return ret
    # run the proxy master and get a score

def main():
    # run spsa for practice before involving the actal proxy master
    # need ( median, stddev) for delay, bandwidth, uplink queue
    # TODO: COME UP WITH BETTER CONSTANTS
    a = 5
    c = 2
    min_theta = np.array([15, .8, 6, .4, 50, 4])
    max_theta = np.array([40, 4, 12, 3, 200, 20])
    theta = np.array([28, 1, 9.6, 1, 175, 10])
    delta = np.array([.3, .05, .2, .04, 10, 2])
    A = .404
    alpha = .602
    gamma = .101
    k = 5
    theta = spsa( run_proxy_master, theta, a, A, alpha, c, gamma, k, delta, min_theta,max_theta)
    print theta

if __name__ == '__main__':
    main()

