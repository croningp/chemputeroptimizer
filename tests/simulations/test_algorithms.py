import argparse
import time
import inspect

import numpy as np

from chemputeroptimizer.algorithms import Random_

import test_functions


functions = dict(inspect.getmembers(test_functions, inspect.isclass))

parser = argparse.ArgumentParser()
parser.add_argument('-n', metavar='N', type=int, default=1,
                    help='number of runs')
parser.add_argument('-d', '--dimension', type=int, metavar='N', default=3,
                    help='xi vector dimension')
parser.add_argument('-a', '--algorithm', type=str,
                    choices=[])
parser.add_argument('-f', '--function', type=str, default='sphere',
                    choices=[k for k in functions])
parser.add_argument('--iterations', type=int, default=1000)

args = vars(parser.parse_args())

test_function = functions[args['function']](args['dimension'])

results = []
optimums = []
params = []
times = []

for _ in range(args['n']):

    constraints = test_function.constraints
    func_results = []
    parameters = []
    optimum = 100500

    algorithm = Random_()

    start_time = time.time()

    while optimum > test_function.optimum:
        vector = algorithm.optimize(
            parameters=parameters,
            results=func_results,
            constraints=constraints,
            )
        parameters.append(vector)
        new_result = test_function(vector)
        func_results.append(new_result)
        optimum = np.amin(func_results)

        if len(func_results) == args['iterations']:
            break

    end_time = time.time()

    processing_time = round(end_time - start_time, 2)
    processing_time *= 1000

    results.append(len(func_results))
    optimums.append(optimum)
    params.append(parameters[np.argmin(func_results)])
    times.append(processing_time)

_index = args['n'] // 50 if args['n'] >= 50 else 10

print(f'Average iterations: {round(np.mean(results))} \u00b1 {round(np.std(results))} \
from {args["n"]} experiments\n\
(best run: {np.min(results)} iterations, worst: {np.max(results)} iterations)\n\
Best result: {np.min(optimums)} (functions optimum: <{test_function.optimum})\n\
Best parameters set: {params[np.argmin(np.min(optimums))]}\n\
Average execution time: {round(np.mean(times), 4)} ms \u00b1 {np.std(times)}\n')

print(f'iterations: ({results[::_index]})\n')
print(f'times: ({times[::_index]})')
