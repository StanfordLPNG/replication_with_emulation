#!/usr/bin/env python

import numpy as np
import random
import copy
import multiprocessing
import proxy_master

# delay mean/std, bandwidth mean/std, uplink_queue mean/std, loss mean/std
reasonable_lower_bounds = np.array([1, 0, 80,  0,    64000, 0, .0,  0])
reasonable_upper_bounds = np.array([9, 0, 110, 0, 64000000, 0, .01, 0])
population_size = 30
assert population_size >= 4, 'need minimum population of 4 for current parent selection'
assert population_size % 2 == 0
step = (reasonable_upper_bounds - reasonable_lower_bounds)/float(population_size + 1)


def get_fitness_score(args, person):
    args['delay'] = (person[0], person[1])
    args['bandwidth'] = (person[2], person[3])
    args['uplink_queue'] = (person[4], person[5])
    args['uplink_loss'] = (person[6], person[7])
    args['downlink_loss'] = (person[6], person[7])

    tput_median_score, delay_median_score =  proxy_master.run_experiment(args)
    fitness = tput_median_score + delay_median_score
    return fitness

def get_single_ip_args(original_args):
    to_ret = []
    for ip in original_args['ips']:
        print ip
        new_args = copy.deepcopy(original_args)
        new_args['ips'] = [ip]
        to_ret.append(new_args)
    return to_ret


def get_fitness_scores(original_args, population):
    # single machine
    if len(original_args['ips']) == 1: #single machine
        return [(get_fitness_score(original_args, person), person) for person in population]

    assert population_size == len(population)
    assert population_size == len(original_args['ips']), 'pop size %d doesnt match length of %s (%d)' % (population_size, original_args['ips'], len(original_args['ips']))
    pool = multiprocessing.Pool(processes=population_size)

    arg_list = get_single_ip_args(original_args)

    assert population_size == len(arg_list)

    workers = []
    for (a, person) in zip(arg_list, population):
        workers.append((pool.apply_async(get_fitness_score, args=(a, person)), person))

    return [(worker.get(), person) for (worker, person) in workers]


def get_elites(number, scored_candidates):
    return sorted(scored_candidates, key=lambda tup: tup[0])[:number]


def get_parent_pair(scored_candidates):
    four_candidates = random.sample(scored_candidates, 4)

    if four_candidates[0][0] < four_candidates[1][0]:
        parent1 = four_candidates[0][1]
    else:
        parent1 = four_candidates[1][1]

    if four_candidates[2][0] < four_candidates[3][0]:
        parent2 = four_candidates[2][1]
    else:
        parent2 = four_candidates[3][1]

    return parent1, parent2


def get_parent_pairs(num_pairs, scored_candidates):
    return [get_parent_pair(scored_candidates) for _ in range(num_pairs)]


def biased_flip(true_probability):
    return random.random() < true_probability


def crossover(a, b):
    assert len(a) == len(b)
    for i in range(len(a)):
        crossover_field = biased_flip(.4)
        if crossover_field:
            a[i], b[i] = b[i], a[i]

def mate((mother, father)):

    print 'mother %s, father %s' % (person_str(mother), person_str(father))
    child1 = mother
    child2 = father

    crossover_probability = .3
    if biased_flip(crossover_probability):
        crossover(child1, child2)

    print 'child1 %s, child2 %s' % (person_str(child1), person_str(child2))
    return child1, child2


def crossover_and_mutate(parent_pairs):
    print 'mating'
    offspring = [mate(parents) for parents in parent_pairs]

    kids1, kids2 = zip(*offspring)

    print 'mutating'

    to_ret = []
    for child in list(kids1)+list(kids2):
        unmutated_child = np.copy(child)
        for i in range(len(child)):
            mutate_field = biased_flip(.2)
            if mutate_field:
                child[i] += (step[i] * random.uniform(-1.5, 1.5))

        child = np.minimum(child, reasonable_upper_bounds)
        child = np.maximum(child, reasonable_lower_bounds)

        if np.array_equal(unmutated_child, child):
            print 'child %s unmutated' % person_str(child)
        else:
            print 'child %s mutated to %s' % (person_str(unmutated_child), person_str(child))

        to_ret.append(child)

    return to_ret


def initialize_population():
    population = []

    delta = reasonable_upper_bounds-reasonable_lower_bounds
    print(delta)
    person = copy.deepcopy(reasonable_lower_bounds)
    for _ in range(population_size):
        for i in range(len(reasonable_lower_bounds)):
            person[i] = reasonable_lower_bounds[i] + (random.random()*delta[i])

        population.append(copy.deepcopy(person))

    return population


def person_str(person):
    return '[%.4f, %.4f, %.4f, %.4f]' % (person[0], person[2], person[4], person[6])


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
    num_elites = 6
    i = 0
    while True:
        i += 1
        scored_population = get_fitness_scores(original_args, population)
        assert len(scored_population) == len(population)

        scored_elites = get_elites(num_elites, scored_population + scored_elites)

        print_stats(i, scored_population, scored_elites)

        parent_pairs = get_parent_pairs(len(population)/2, scored_population)
        children = crossover_and_mutate(parent_pairs)

        assert len(children) == len(population)
        population = children


if __name__ == '__main__':
    main()

