"""Random search"""

import random

import numpy as np

from ..algorithms import AbstractAlgorithm


class Random_(AbstractAlgorithm):

    DEFAULT_CONFIG = {}

    def __init__(self, dimensions=None, config=None):
        self.name = 'random'
        super().__init__(dimensions, config)

    def suggest(self, parameters=None, results=None, constraints=None):

        if constraints is None:
            constraints = self.dimensions

        self.logger.debug('random optimizer for the following parameters: \n\
parameters: %s\nresults: %s\nconstraints: %s\n',
                          parameters, results, constraints)

        return np.array(
            [round(random.uniform(a, b), 2) for a, b in constraints])
