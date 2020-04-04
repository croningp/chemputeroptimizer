"""Defines abstact algorithm class"""

import logging

from abc import ABC, abstractmethod


class AbstractAlgorithm(ABC):
    """Default constructor for algorithmic optimisation.

    Provides general methods to load parameters data, parse it into data arrays,
    sort the data according to the target value, map and validate the data against
    the experimental parameters, save the iteration for further access.

    Attributes:
        dimensions (List[Tuple[int, int]], optinal): Search space dimensions,
            list of (min, max) tuples for each input data point.
    """
    def __init__(self, dimensions=None):
        if not hasattr(self, 'name'): self.name = self.__class__.__name__
        self.logger = logging.getLogger(f'optimizer.algorithm.{self.name}')
        self.dimensions = dimensions

    @abstractmethod
    def optimize(self, parameters, results, constraints=None):
        """Find the parameters for the next iteration.

        Uses the experimental matrixes to find new parameter set through
        given optimisation algorithm. Replaces the worst parameter with new points
        setting the target value to -1.
        This method has to be redefined in ancestor classes.

        Args:
            parameters (:obj: np.array): (n x i) size matrix where n is number of experiments and i
                is number of experimental parameters.
            results (:obj: np.array): (n x j) size matrix where j is number of the target parameters.
            constraints (Any): tuple with min/max values for the parameters

        Returns:
            (np.array): An array with new set of experimental input parameters.
        """

