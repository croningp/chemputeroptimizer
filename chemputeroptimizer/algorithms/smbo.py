"""Sequential model-based optimization using scikit-optimize."""

from skopt import Optimizer

import numpy as np

from ..algorithms import AbstractAlgorithm


class SMBO(AbstractAlgorithm):
    """
    Wraps skopt.Optimizer to minimize expensive/noisy black-box functions.
    Several methods for sequential model-based optimization are available.

    Attributes:
        skopt_optimizer: skopt Optimizer instance, for details see:
        https://scikit-optimize.github.io/stable/modules/generated/skopt.Optimizer.html
        dimensions (list): List of search space dimensions. Can be defined as
            - a `(lower_bound, upper_bound)` tuple (for `Real` or `Integer`
            dimensions),
            - a `(lower_bound, upper_bound, "prior")` tuple (for `Real`
            dimensions),
            - as a list of categories (for `Categorical` dimensions), or
            - an instance of a `Dimension` object (`Real`, `Integer` or
            `Categorical`).
        base_estimator (str): `"GP"`, `"RF"`, `"ET"`, `"GBRT"` or sklearn regressor.
        n_initial_points (int) : Number of evaluations of `func` with random
            initialization points before approximating it with `base_estimator`.
        acq_func (string): Function to minimize over the posterior distribution.
    """

    DEFAULT_CONFIG = {
        "base_estimator": "GP",
        "acq_func": "EI",
        "n_initial_points": 5,
        # below are defaults for the skopt Optimizer
        "acq_optimizer": "auto",
        "random_state": None,
        "acq_func_kwargs": None,
        "acq_optimizer_kwargs": None,
    }

    def __init__(self, dimensions, config=None):

        super().__init__(dimensions=dimensions, config=config)

        self.skopt_optimizer = Optimizer(dimensions=dimensions, **self.config)

    def initialise(self):
        pass

    def suggest(self, parameters=None, results=None, constraints=None):
        # only last row is passed to skopt.Optimizer, since
        # all previous data is stored inside
        if parameters is not None and parameters.size != 0:
            parameters = parameters[-1].tolist()
        if results is not None and results.size != 0:
            results = results[-1].tolist()
            if len(results) == 1:
                self.skopt_optimizer.tell(parameters, -results[0])
            else:
                raise ValueError('Only one result is supported for SMBO algorithm!')
        return np.array(self.skopt_optimizer.ask())

    def _check_termination(self):
        pass
