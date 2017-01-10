#!/usr/bin/env python
import random

total_time = 1000 * 30  # 60 sec trace
cur_time = 1

# can't go above 12
mbps_max = 9.8
mbps_min = 7.3

def mbps_to_ppms(mbps):
    return ((mbps/8.)*1024.*1024.)/(1000.*1500.)

max_packets_per_ms = mbps_to_ppms(mbps_max)
min_packets_per_ms = mbps_to_ppms(mbps_min)

cur_packets_per_ms = max_packets_per_ms

# every 100ms decide how many departure events to have
with open('randwalk.trace', 'w') as trace:
    while cur_time < total_time:
        rnd = random.random()
        #print('Random: %.4f cur_packets_per_ms %.4f' % (rnd, cur_packets_per_ms))
        if rnd < cur_packets_per_ms:
            #print('%d' % cur_time)
            trace.write('%d\n' % cur_time)

        if random.getrandbits(1):
            cur_packets_per_ms += .003
        else:
            cur_packets_per_ms -= .002

        cur_packets_per_ms = min(cur_packets_per_ms, max_packets_per_ms)
        cur_packets_per_ms = max(cur_packets_per_ms, min_packets_per_ms)
        cur_time += 1
