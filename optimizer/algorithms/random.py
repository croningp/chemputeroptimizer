"""Random search"""

import random

import numpy as np

from ..algorithms import AbstractAlgorithm

class Random_(AbstractAlgorithm):
    def __init__(self, max_iterations):
        super().__init__(max_iterations)

    def optimize(self, parameters, results, constraints=None):

        print(
            'random optimizer for the following parameters: \n',
            f'parameters: {parameters} \n',
            f'results: {results} \n',
            f'contstrains: {constraints} \n'
        )

        return np.array(
            [random.uniform(a, b) for a, b in constraints]
        )

    def initialise(self):
        pass

    def _check_termination(self):
        pass