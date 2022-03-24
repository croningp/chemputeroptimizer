"""Random search"""

from typing import Optional

import numpy

from ..algorithms import AbstractAlgorithm


class Random_(AbstractAlgorithm):
    """ Random search algorithm.

    Outputs random numbers within the given constraints. Randomly.
    """

    DEFAULT_CONFIG = {
        'random_state': 42,
    }

    def __init__(self, dimensions=None, config=None):
        self.name = 'random'

        super().__init__(dimensions, config)

        self.rng = numpy.random.default_rng(self.config['random_state'])

    def suggest(
        self,
        parameters: Optional[numpy.ndarray] = None,
        results: Optional[numpy.ndarray] = None,
        constraints: Optional[numpy.ndarray] = None,
        n_batches: int = 1,
        n_returns: int = 1,
    ):

        if constraints is None:
            constraints = self.dimensions

        self.logger.debug('Random optimizer for the following parameters: \n\
parameters: %s\nresults: %s\nconstraints: %s\n',
                          parameters, results, constraints)
        # Forging new setup
        new_setup = []
        for _ in range(n_returns):
            new_setup.append(
                [round(self.rng.uniform(a, b), 2) for a, b in constraints]
            )

        # Casting to numpy array
        return numpy.array(new_setup)
