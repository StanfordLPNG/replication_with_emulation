#!/usr/bin/env python

import numpy as np
import random
import copy
import multiprocessing
import proxy_master

# delay mean/std, bandwidth mean/std, uplink_queue mean/std, uplink_loss mean/std, downlink_loss mean/std, prepend/append bool
reasonable_lower_bounds = np.array([25, 0,  8, 0,  10, 0, .0, 0, .0, 0, 0.])
reasonable_upper_bounds = np.array([35, 0, 12, 0, 500, 0, .1, 0, .1, 0, 1.])
max_mutation = np.array([2, 0, .5, 0, 5, 0, .005, 0, .005, 0, 1])


def get_fitness_score(args, person, save_logs):
    args['delay'] = (person[0], person[1])
    args['bandwidth'] = (person[2], person[3])
    args['uplink_queue'] = (person[4], person[5])
    args['uplink_loss'] = (person[6], person[7])
    args['downlink_loss'] = (person[8], person[9])
    args['append'] = person[10] > .5

    return proxy_master.run_experiment(args, save_logs)

def get_single_ip_args(original_args):
    to_ret = []
    for ip in original_args['ips']:
        print ip
        new_args = copy.deepcopy(original_args)
        new_args['ips'] = [ip]
        to_ret.append(new_args)
    return to_ret


def get_fitness_scores(original_args, population, save_logs):
    # single machine
    if len(original_args['ips']) == 1: #single machine
        return [(get_fitness_score(original_args, person, save_logs), person) for person in population]

    assert population_size == len(population)
    assert population_size == len(original_args['ips']), 'pop size %d doesnt match length of %s (%d)' % (population_size, original_args['ips'], len(original_args['ips']))
    pool = multiprocessing.Pool(processes=population_size)

    arg_list = get_single_ip_args(original_args)

    assert population_size == len(arg_list)

    workers = []
    for (a, person) in zip(arg_list, population):
        workers.append((pool.apply_async(get_fitness_score, args=(a, person, save_logs)), person))

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
        crossover_field = biased_flip(.25)
        if crossover_field:
            a[i], b[i] = b[i], a[i]

def mate((mother, father)):

    child1 = np.copy(mother)
    child2 = np.copy(father)

    crossover_probability = .4
    if biased_flip(crossover_probability):
        crossover(child1, child2)

    if np.array_equal(mother, child1):
        print 'mother %s, father %s' % (person_str(mother), person_str(father))
        print 'child1 %s, child2 %s' % (person_str(child1), person_str(child2))
    else:
        print 'mother %s, father %s cloned to next generation' % (person_str(mother), person_str(father))

    return child1, child2


def crossover_and_mutate(parent_pairs):
    print 'mating'
    offspring = [mate(parents) for parents in parent_pairs]

    kids1, kids2 = zip(*offspring)

    print 'mutating'

    major_mutation = False
    to_ret = []
    for child in list(kids1)+list(kids2):
        unmutated_child = np.copy(child)
        for i in range(len(child)):
            mutate_field = biased_flip(.2)
            if mutate_field:
                major_mutation = biased_flip(.1)
                if major_mutation:
                    child[i] = random.uniform(reasonable_lower_bounds[i], reasonable_upper_bounds[i])
                else:  # normal mutation
                    child[i] += (max_mutation[i] * random.uniform(-1, 1))

        child = np.minimum(child, reasonable_upper_bounds)
        child = np.maximum(child, reasonable_lower_bounds)

        if np.array_equal(unmutated_child, child):
            print 'child %s unmutated' % person_str(child)
        else:
            print 'child %s mutated to %s' % (person_str(unmutated_child), person_str(child))
            if major_mutation:
                print 'major mutation'


        to_ret.append(child)

    return to_ret


def initialize_population():
    population = []

    person = copy.deepcopy(reasonable_lower_bounds)
    for _ in range(population_size):
        for i in range(len(reasonable_lower_bounds)):
            person[i] = random.uniform(reasonable_lower_bounds[i], reasonable_upper_bounds[i])

        population.append(copy.deepcopy(person))

    return population


def person_str(person):
    return '[%.4f, %.4f, %.4f, %.4f, %.4f, %r]' % (person[0], person[2], person[4], person[6], person[8], person[10] > .5)

def print_scored_person_list(scored_person_list):
    for (score, person) in scored_person_list:
        print 'score=%.2f params=%s' % (score, person_str(person))


def print_stats(generation, runs_per_ip, scored_population, scored_elites):
    print "GENETIC GENERATION %d with %d runs per ip" % (generation, runs_per_ip)
    print 'delay mean, bandwidth mean, uplink_queue mean, uplink_loss mean, downlink_loss mean'
    print "Population:"
    print_scored_person_list(scored_population)
    print "Elites:"
    print_scored_person_list(scored_elites)


def main():

    original_args = proxy_master.get_args() # same arguments from proxy master

    global population_size
    population_size = max(4, len(original_args['ips']))

    assert population_size >= 4, 'need minimum population of 4 for current parent selection'
    assert population_size % 2 == 0

    population = initialize_population()
    print "INITIAL POPULATION"
    for person in population:
        print(person_str(person))

    scored_elites = []
    num_elites = (population_size+1)/5
    i = 0
    save_logs = False
    while True:
        i += 1

        if i < 5:
            original_args['runs_per_ip'] = 1
        elif i < 15:
            original_args['runs_per_ip'] = 2
        else:
            original_args['runs_per_ip'] = 10
            save_logs = True

        scored_population = get_fitness_scores(original_args, population, save_logs)
        assert len(scored_population) == len(population)


        if i == 5:
            print "drop elites when moving to 2 experiments"
            scored_elites = get_elites(num_elites, scored_population)
        if i == 15:
            print "drop elites when moving to 10 experiments"
            scored_elites = get_elites(num_elites, scored_population)
        else:
            scored_elites = get_elites(num_elites, scored_population + scored_elites)

        print_stats(i, original_args['runs_per_ip'], scored_population, scored_elites)

        parent_pairs = get_parent_pairs(len(population)/2, scored_population)
        children = crossover_and_mutate(parent_pairs)

        assert len(children) == len(population)
        population = children


if __name__ == '__main__':
    main()

