#!/usr/bin/env python

import re
import sys
import heapq
def get_params(search_log_name):
    print search_log_name
    search_log = open(search_log_name, 'r', 0)
    p = re.compile(
        'bandwidth=(.*?),delay=(.*?),uplink_queue=(.*?),'
        'uplink_loss=(.*?),downlink_loss=(.*?),'
        'tput_median_score=(.*?),delay_median_score=(.*?),overall_median_score=(.*?)\n')

    strs = {"target": [], "bandwidth": [], "delay": [], "uplink_queue":[], "uplink_loss": [], "downlink_loss": []}


    for line in search_log:
        m = p.match(line)
        if m:
            strs['target'].append('%.2f' % float(m.group(8)))
            strs['bandwidth'].append('%.2f' % float(m.group(1)))
            strs['delay'].append('%d' % float(m.group(2)))
            strs['uplink_queue'].append('%d' % float(m.group(3)))
            strs['uplink_loss'].append('%.3f' % float(m.group(4)))
            strs['downlink_loss'].append('%.3f' % float(m.group(5)))

    params = {}
    for i in ["target", "bandwidth", "delay", "uplink_queue", "uplink_loss", "downlink_loss"]:
        if i != "uplink_queue":
            params[i] = map(float, strs[i])
        else:

            params[i] = map(int, strs[i])
    # find the two with the best score
    print "PARAMS : {}".format(params)
    search_log.close()
    return params

def get_best_n(n, search_log_name):
    params = get_params(search_log_name)
    smallest =  heapq.nsmallest(n, params['target'])
    smallest.reverse()
    smallest_indices = [params['target'].index(i) for i in smallest]
    best_points = [[params["bandwidth"][i], params["delay"][i], params["uplink_queue"][i], params["uplink_loss"][i], params["downlink_loss"][i]] for i in smallest_indices]
    best_points.reverse()
    print best_points, smallest
    return best_points, smallest

def parse_search_log_for_priors(priors,name):
    params = get_params(name)
    for key in priors:
        priors[key].extend(params[key])
    return priors
def main():
    get_best_n(3, 'col_search_log')
if __name__ == '__main__':
    main()
