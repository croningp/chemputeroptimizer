"""
Dummy "algorithm" to output the parameters from already performed experiments.
Used, as the name suggest, to check reproducibility of the platform.
"""

import random
from typing import Optional

import numpy
from numpy.random import Generator

from .base_algorithm import AbstractAlgorithm


class Reproduce(AbstractAlgorithm):

    DEFAULT_CONFIG = {
        'random_state': 42,  # random state for selecting parameters
        'selected_experiments': [],  # if only selected indices
    }

    def __init__(self, dimensions=None, config=None):

        self.name = 'reproduce'

        super().__init__(dimensions=dimensions, config=config)

        self.rng: Generator = numpy.random.default_rng(
            self.config['random_state'])

        self.counter: int = 0  # counting number of experiments

    def suggest(
        self,
        parameters: Optional[numpy.ndarray] = None,
        results: Optional[numpy.ndarray] = None,
        constraints: Optional[numpy.ndarray] = None,
        n_batches: int = 1,
        n_returns: int = 1,
    ) -> numpy.ndarray:

        # Removing already repeated experiments
        if self.counter != 0:
            parameters = parameters[:-self.counter]

        # Selecting experiments
        # Direct indexes have higher priority
        if self.config['selected_experiments']:
            new_setup = []
            for i in range(n_returns):
                i += self.counter
                try:
                    new_setup.append(
                        parameters[self.config['selected_experiments'][i]]
                    )
                except IndexError:
                    new_setup.append(
                        parameters[self.config['selected_experiments'][-1]]
                    )
        else:
            new_setup = self.rng.choice(
                parameters,
                n_returns,
                replace=False,
                shuffle=False,
            )

        self.logger.debug('Reproducing experiments with parameters:\n%r\n',
                          new_setup)

        # Updating number of experiments
        self.counter += n_returns

        return numpy.atleast_2d(new_setup)
