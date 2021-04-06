""" Dummy "algorithm" to output the same parameter setup as input. """

from typing import Optional

import numpy

from ..algorithms import AbstractAlgorithm


class Reproduce(AbstractAlgorithm):

    DEFAULT_CONFIG = {}

    def __init__(self, dimensions=None, config=None):
        self.name = 'reproduce'
        super().__init__(dimensions, config)

    def suggest(
        self,
        parameters: Optional[numpy.ndarray] = None,
        results: Optional[numpy.ndarray] = None,
        constraints: Optional[numpy.ndarray] = None,
        n_batches: int = -1,
        n_returns: int = 1,
    ) -> numpy.ndarray:

        return parameters[-n_returns:]
