"""Random search"""

import random

import numpy as np

from ..algorithms import AbstractAlgorithm

class Random_(AbstractAlgorithm):
    def __init__(self):
        super().__init__()

    def optimize(self, parameters, results, constraints=None):

        print(
            'random optimizer for the following parameters: \n',
            f'parameters: {parameters} \n',
            f'results: {results} \n',
            f'contstrains: {constraints} \n'
        )

        return np.array(
            [round(random.uniform(a, b), 2) for a, b in constraints]
        )

    def initialise(self):
        pass

    def _check_termination(self):
        pass