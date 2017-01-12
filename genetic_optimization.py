#!/usr/bin/env python

import numpy as np
import random
import multiprocessing
import proxy_master

# delay mean/std, bandwidth mean/std, uplink_queue mean/std, uplink_loss mean/std, downlink_loss mean/std
reasonable_lower_bounds = np.array([  5, 0,  1, 0,  10, 0, .0, 0, .0, 0])
reasonable_upper_bounds = np.array([150, 0, 20, 0, 500, 0, .1, 0, .1, 0])
population_size = 4
assert population_size % 2 == 0
step = (reasonable_upper_bounds - reasonable_lower_bounds)/float(population_size + 1)


def get_fitness_score(args, person):
    args['delay'] = (person[0], person[1])
    args['bandwidth'] = (person[2], person[3])
    args['uplink_queue'] = (person[4], person[5])
    args['uplink_loss'] = (person[6], person[7])
    args['downlink_loss'] = (person[8], person[9])

    tput_median_score, delay_median_score =  proxy_master.run_experiment(args)
    fitness = tput_median_score + delay_median_score
    return fitness

def get_single_ip_args(original_args):
    to_ret = []
    for ip in original_args['ips']:
        print ip
        new_args = original_args
        new_args['ips'] = [ip]
        to_ret.append(new_args)
    return to_ret


def get_fitness_scores(original_args, population):
    return [(get_fitness_score(original_args, person), person) for person in population]

#def get_fitness_scores(original_args, population):
#    ips = original_args['ips']
#    #pool = multiprocessing.Pool(processes=len(ips))
#    pool = multiprocessing.Pool(processes=1)
#
#    assert len(population) % len(ips) == 0, 'inefficient'
#
#    parallel_rounds = len(population) / len(ips)
#
#    to_ret = []
#    for i in range(parallel_rounds):
#        arg_list = get_single_ip_args(original_args)
#        assert (len(arg_list) * parallel_rounds) == len(population)
#
#        workers = []
#        for j in range(len(arg_list)):
#            person = population[i*j]
#            workers.append((pool.apply_async(get_fitness_score, args=(arg_list[j], person)), person))
#
#        for (worker, person) in workers:
#            to_ret.append((worker.get(), person))
#
#    return to_ret

def get_elites(number, scored_candidates):
    return sorted(scored_candidates, key=lambda tup: tup[0])[:number]


def get_parent(scored_candidates):
    [a, b] = random.sample(scored_candidates, 2)
    if a[0] < b[0]:
        return a[1]
    else:
        return b[1]

def get_parent_pairs(num_pairs, scored_candidates):
    return [(get_parent(scored_candidates), get_parent(scored_candidates)) for _ in range(num_pairs)]


def biased_flip(true_probability):
    return random.random() < true_probability


def crossover(a, b):
    assert len(a) == len(b)
    for i in range(len(a)):
        crossover_field = biased_flip(.4)
        if crossover_field:
            a[i], b[i] = b[i], a[i]

def sex((mother, father)):
    crossover_probability = .7

    print 'mother %s, father %s' % (person_str(mother), person_str(father))
    child1 = mother
    child2 = father

    if biased_flip(crossover_probability):
        crossover(child1, child2)

    print 'child1 %s, child2 %s' % (person_str(child1), person_str(child2))
    return child1, child2


def crossover_and_mutate(parent_pairs):
    offspring = [sex(parents) for parents in parent_pairs]

    kids1, kids2 = zip(*offspring)

    to_ret = []
    for child in list(kids1)+list(kids2):
        for i in range(len(child)):
            mutate_field = biased_flip(.2)
            if mutate_field:
                if biased_flip(.5):
                    child[i] += (step[i] / 2.)
                else:
                    child[i] -= (step[i] / 2.)

        child = np.minimum(child, reasonable_upper_bounds)
        child = np.maximum(child, reasonable_lower_bounds)
        to_ret.append(child)

    return to_ret


def initialize_population():
    population = []
    for i in range(1, population_size + 1):
        population.append(reasonable_lower_bounds + (i * step))

    return population


def person_str(person):
    return '[%.4f, %.4f, %.4f, %.4f, %.4f]' % (person[0], person[2], person[4], person[6], person[8])


def print_scored_person_list(scored_person_list):
    for (score, person) in scored_person_list:
        print 'score=%.2f params=%s' % (score, person_str(person))


def print_stats(generation, scored_population, scored_elites):
    print "GENETIC GENERATION %d" % generation
    print 'delay mean, bandwidth mean, uplink_queue mean, uplink_loss mean, downlink_loss mean'
    print "Population:"
    print_scored_person_list(scored_population)
    print "Elites:"
    print_scored_person_list(scored_elites)


def main():
    original_args = proxy_master.get_args() # same arguments from proxy master
    population = initialize_population()
    print "INITIAL POPULATION"
    for person in population:
        print(person_str(person))

    scored_elites = []
    num_elites = 2
    for i in range(3):
        scored_population = get_fitness_scores(original_args, population)
        assert len(scored_population) == len(population)

        scored_elites = get_elites(num_elites, scored_population + scored_elites)

        print_stats(i, scored_population, scored_elites)

        parent_pairs = get_parent_pairs(len(population)/2, scored_population + scored_elites)
        children = crossover_and_mutate(parent_pairs)

        assert len(children) == len(population)
        population = children


if __name__ == '__main__':
    main()

