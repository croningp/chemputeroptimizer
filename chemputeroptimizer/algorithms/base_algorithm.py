"""Defines abstact algorithm class"""

import logging

from abc import ABC, abstractmethod


class AbstractAlgorithm(ABC):
    """Default constructor for algorithmic optimisation.

    Provides general methods to load parameters data, parse it into data arrays,
    sort the data according to the target value, map and validate the data against
    the experimental parameters, save the iteration for further access.

    Attributes:
        dimensions (Iterable[Iterable[float, float]], optinal): Search space
            dimensions, e.g. list of (min, max) tuples for each input data point.
        config (Dict, optional): All neccessary attributes for specific
            algorithm. If not supplied, default class attribute is
            used instead.
    """
    # all config attributes neccessary for specific algorithm
    DEFAULT_CONFIG = {}

    def __init__(self, dimensions=None, config=None):
        if not hasattr(self, 'name'): self.name = self.__class__.__name__
        self.logger = logging.getLogger(f'optimizer.algorithm.{self.name}')
        try:
            self.dimensions = list(dimensions)
        except TypeError:
            raise TypeError('Dimensions must be iterable!') from None
        self.config = self.DEFAULT_CONFIG.copy()
        if config:
            self.config.update(config)

    @abstractmethod
    def suggest(self, parameters=None, results=None, constraints=None):
        """Find the parameters for the next iteration.

        Uses the experimental matrixes to find new parameter set through
        given optimisation algorithm.

        This method has to be redefined in ancestor classes.

        Args:
            parameters (:obj: np.array, optional): (n x i) size matrix where n
                is number of experiments and i is number of experimental
                parameters.
            results (:obj: np.array, optional): (n x j) size matrix where j is
                number of the target parameters.
            constraints (Any, optional): tuple with min/max values for the
                parameters

        Returns:
            (np.array): An array with new set of experimental input parameters.
        """
