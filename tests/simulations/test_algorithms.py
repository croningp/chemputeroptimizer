"""Test for algorithms"""

import argparse
import time
import inspect

from matplotlib import pyplot as plt
import numpy as np
import pandas as pd

import chemputeroptimizer.algorithms as all_algorithms

import test_functions

functions = dict(inspect.getmembers(test_functions, inspect.isclass))
algorithms = dict(inspect.getmembers(all_algorithms, inspect.isclass))

parser = argparse.ArgumentParser()
parser.add_argument('-n', metavar='N', type=int, default=1,
                    help='number of runs')
parser.add_argument('-d', '--dimension', type=int, metavar='N', default=3,
                    help='xi vector dimension')
parser.add_argument('-a', '--algorithm', type=str, default='Random_',
                    choices=['Random_', 'SMBO'])
parser.add_argument('-f', '--function', type=str, default='sphere',
                    choices=[k for k in functions])
parser.add_argument('--iterations', type=int, default=1000)

args = vars(parser.parse_args())

test_function = functions[args['function']](args['dimension'])

results = []
optimums = []
params = []
times = []
data = []

for _ in range(args['n']):

    constraints = test_function.constraints
    parameters = np.empty((0, len(constraints)))
    func_results = np.empty((0, 1))
    optimum = 999999
    best_results = []

    algorithm = algorithms[args['algorithm']](constraints)
    start_time = time.time()

    while optimum > test_function.target:
        vector = algorithm.suggest(
            parameters=parameters,
            results=func_results,
            constraints=constraints,
            )
        parameters = np.vstack((parameters, vector))
        new_result = test_function(vector)
        func_results = np.vstack((func_results, new_result))
        optimum = np.amin(func_results)
        best_results.append(optimum)

        if len(func_results) == args['iterations']:
            break

    end_time = time.time()

    processing_time = round(end_time - start_time, 4)
    processing_time *= 1000

    data.append(best_results)
    results.append(len(func_results))
    optimums.append(optimum)
    params.append(parameters[np.argmin(func_results)])
    times.append(processing_time)

    # replacement for tqdm
    if len(results) == 1:
        print(f'Iteration took {processing_time} ms, {args["n"] - 1} more\
 iterations to go.')

_index = args['n'] // 50 if args['n'] >= 50 else 10

# Report results
print(f'Average iterations: {round(np.mean(results))} \u00b1 {round(np.std(results))} \
from {args["n"]} experiments\n\
(best run: {np.min(results)} iterations, worst: {np.max(results)} iterations)\n\
Best result: {np.min(optimums)} (Target: <{test_function.target})\n\
Best parameters set: {params[np.argmin(np.min(optimums))]}\n\
Average execution time: {round(np.mean(times), 4)} ms \u00b1 {np.std(times)}\n')

print(f'iterations: ({results[::_index]})\n')
print(f'times: ({times[::_index]})')

# Visualize results
df = pd.DataFrame(data)
df = df.fillna(axis=1, method="ffill")
upper = np.mean(df, axis=0)+np.std(df, axis=0)
lower = np.mean(df, axis=0)-np.std(df, axis=0)
average = np.mean(df, axis=0)
idx = list(df.columns)
report = f"{args['algorithm']} on {args['function']} ({args['n']} \u00d7\
 {args['iterations']}) iterations"
plt.figure()
plt.title(report)
plt.xlabel("Iterations")
plt.xlim(0, round(np.mean(results) + np.std(results)))
plt.ylabel("Best result")
plt.ylim(test_function.optimum, average.max())
plt.plot(idx, average, label=algorithm.__class__.__name__)
plt.fill_between(idx, upper, lower, facecolor='blue', alpha=0.1)
plt.axhline(y=test_function.target, color='k',
            linestyle='--', label=f'Target ({test_function.target:.02f})')
# plt.axhline(y=test_function.optimum, color='k', linestyle='-', label='True optimum')
plt.legend(frameon=False)
plt.show()
