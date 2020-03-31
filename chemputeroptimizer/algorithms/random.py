"""Random search"""

import random

import numpy as np

from ..algorithms import AbstractAlgorithm


class Random_(AbstractAlgorithm):

    def __init__(self, dimensions=None):
        self.name = 'random'
        super().__init__(dimensions)

    def optimize(self, parameters, results, constraints=None):

        if constraints is None:
            constraints = self.dimensions

        self.logger.debug('random optimizer for the following parameters: \n\
parameters: %s\nresults: %s\nconstraints: %s\n',
                          parameters, results, constraints)

        # print('random optimizer for the following parameters: \n',
        #       f'parameters: {parameters} \n', f'results: {results} \n',
        #       f'constraints: {constraints} \n')

        return np.array(
            [round(random.uniform(a, b), 2) for a, b in constraints])

    def initialise(self):
        pass

    def _check_termination(self):
        pass
