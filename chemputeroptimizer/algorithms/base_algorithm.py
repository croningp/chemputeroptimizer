"""Defines abstact algorithm class"""

import logging

from abc import ABC, abstractmethod
from typing import Optional

import numpy


class AbstractAlgorithm(ABC):
    """Default constructor for algorithmic optimisation.

    Provides general methods to load parameters data, parse it into data arrays,
    sort the data according to the target value, map and validate the data
    against the experimental parameters, save the iteration for further access.

    Attributes:
        dimensions (Iterable[Iterable[float, float]], optional): Search space
            dimensions, e.g. list of (min, max) tuples for each input data
            point.
        config (Dict, optional): All necessary attributes for specific
            algorithm. If not supplied, default class attribute is
            used instead.
    """
    # All config attributes necessary for specific algorithm
    DEFAULT_CONFIG = {}

    def __init__(self, dimensions=None, config=None):
        """ Default constructor.

        Should contain all setup method to initialize the algorithm.

        If redefined in the ancestor classes, should be called to setup the
        logger.
        """
        if not hasattr(self, 'name'):
            self.name = self.__class__.__name__
        self.logger = logging.getLogger(f'optimizer.algorithm.{self.name}')
        try:
            self.dimensions = list(dimensions)
        except TypeError:
            raise TypeError('Dimensions must be iterable!') from None
        self.config = self.DEFAULT_CONFIG.copy()
        if config:
            self.config.update(config)

    @abstractmethod
    def suggest(
        self,
        parameters: Optional[numpy.ndarray] = None,
        results: Optional[numpy.ndarray] = None,
        constraints: Optional[numpy.ndarray] = None,
        n_batches: int = -1,
        n_returns: int = 1,
    ) -> numpy.ndarray:
        """Find the parameters for the next iteration.

        Uses the experimental matrixes to find new parameter set through
        given optimisation algorithm. The last "n_batches" rows of the
        experiment matrix correspond to the latest results and should be used
        to output new "n_returns" x number of parameters suggested setup. If
        "n_batches" == -1, full experiment matrix should be used for calculation
        of the next setup. This is used, when preloading the results from the
        previous experiments.

        This method has to be redefined in ancestor classes.

        Args:
            parameters (:obj: np.array, optional): (n x i) size matrix where n
                is number of experiments and i is number of experimental
                parameters.
            results (:obj: np.array, optional): (n x j) size matrix where j is
                number of the target parameters.
            constraints (Any, optional): tuple with min/max values for the
                parameters.
            n_batches (int): Number of latest experiments (batches).
            n_returns (int): Number of new parameter sets to return.

        Returns:
            (np.array): An ("n_returns" x i) matrix with new set(s) of
                experimental input parameters.
        """
