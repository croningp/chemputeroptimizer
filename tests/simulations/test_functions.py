""" Test functions for optimization problems."""

from abc import ABC, abstractmethod

import numpy as np


class AbstractTestFunction(ABC):
    """Basic class for optimization test functions

    Arguments:
        dimension (int, optional): xi vector dimension
    """

    optimum = None
    target = None
    constraints = (None, None)
    optimum_parameters = None

    def __init__(self, dimension=2):

        self.constraints = [self.constraints for _ in range(dimension)]
        self.optimum_parameters = [self.optimum_parameters
                                   for _ in range(dimension)]
        self.dimension = dimension

    @abstractmethod
    def __call__(self, vector):
        """Defines functions behaviour

        Args:
            vector (Union[np.array, List]): xi vector of size
                "dimension"
        Returns:
            int: function result
        """

class sphere(AbstractTestFunction):
    """
    Python implementation of sphere function. Dimensions: d
    Input Domain: hypercube xi ∈ [-5.12, 5.12], for all i = 1, …, d.
    Global optimum: f(x*) = 0 for x* = (0,...,0)
    Details: https://www.sfu.ca/~ssurjano/spheref.html
    """

    optimum = 0
    target = 1 # some threshold here
    constraints = (-5.12, 5.12)
    optimum_parameters = 0


    def __call__(self, vector):
        # convert to np.array
        if isinstance(vector, list):
            vector = np.array(vector)

        result = np.sum(vector**2)
        return result

class rosenbrock(AbstractTestFunction):
    """
    Python implementation of rosenbrock function.
    Dimensions: d. The function is unimodal, and the global minimum lies in
    a narrow, parabolic valley. Input Domain: hypercube xi ∈ [-5, 10],
    for all i = 1, …, d, or xi ∈ [-2.048, 2.048], for all i = 1, …, d.
    Global Minimum: f(x*) = 0 for x* = (1,...,1)
    Details: https://en.wikipedia.org/wiki/Rosenbrock_function
    """
    optimum = 0
    target = 10 # some threshold here
    constraints = (-2.048, 2.048)
    optimum_parameters = 1

    def __call__(self, vector):
        # convert to np.array
        if isinstance(vector, list):
            vector = np.array(vector)
        result = 0

        for idx, v in enumerate(vector[:-1]):
            result += 100 * (vector[idx + 1] - v**2) ** 2 + (1 - v) ** 2
        return np.array(round(result, 2))


class styblinski_tang(AbstractTestFunction):
    """
    Python implementation of Styblinski-Tang function.
    Dimensions: d. The function is usually evaluated on the hypercube
    xi ∈ [-5, 5],, for all i = 1, …, d. Global Minimum: 39.16 * d
    Details: https://www.sfu.ca/~ssurjano/stybtang.html
    """
    optimum = -39.16
    target = -38 # some threshold here
    constraints = (-5., 5.)
    optimum_parameters = 1

    def __init__(self, dimension=2):
        self.optimum = self.optimum * dimension
        self.target = self.target * dimension
        super().__init__(dimension=dimension)

    def __call__(self, vector):
        if isinstance(vector, list):
            vector = np.array(vector)
        result = 0
        result = 0.5 * np.sum(vector**4.0 - 16*vector**2.0 + 5.0*vector)
        return np.array(round(result, 2))


class schwefel(AbstractTestFunction):
    """
    Python implementation of Schwefel function.
    Dimensions: d. Complex, many local minima.
    Input Domain: hypercube xi ∈ [-500, 500], for all i = 1, …, d.
    Global Minimum: f(x*) = 0, for x* = (420.9687,...,420.9687
    Details: https://www.sfu.ca/~ssurjano/schwef.html
    """
    optimum = 0
    target = 10 # some threshold here
    constraints = (-500., 500.)
    optimum_parameters = 420.9687

    def __call__(self, vector):
        if isinstance(vector, list):
            vector = np.array(vector)
        result = 0
        result = 418.9829 * self.dimension - np.sum(vector*np.sin(np.sqrt(abs(vector))))
        return np.array(round(result, 2))

def noise(factor):
    """
    Function to add random noise.
    """
    return factor * np.random.randn()
