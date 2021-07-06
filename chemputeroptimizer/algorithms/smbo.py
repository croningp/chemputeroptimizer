"""Sequential model-based optimization using scikit-optimize.

For details see:
https://scikit-optimize.github.io/stable/modules/generated/skopt.Optimizer.html
"""

from typing import Optional, Union

from skopt import Optimizer

import numpy

from ..algorithms import AbstractAlgorithm


class SMBO(AbstractAlgorithm):
    """
    Wraps skopt.Optimizer to minimize expensive/noisy black-box functions.
    Several methods for sequential model-based optimization are available.
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
        "initial_point_generator":'random'
    }

    def __init__(self, dimensions, config=None):

        self.name = "smbo"

        super().__init__(dimensions=dimensions, config=config)

        self.skopt_optimizer = Optimizer(dimensions=dimensions, **self.config)

    def suggest(
        self,
        parameters: Optional[numpy.ndarray] = None,
        results: Optional[numpy.ndarray] = None,
        constraints: Optional[numpy.ndarray] = None,
        n_batches: int = 1,
        n_returns: int = 1,
    ):
        # Negating results, if present
        # Since skopt optimizer assumes minimization of the cost function
        if results is not None and isinstance(results, numpy.ndarray):
            results = -results # pylint: disable=invalid-unary-operand-type

        # If all experiments should be taken into account
        if n_batches == -1:
            n_batches = 0

        if parameters is not None and results is not None:
            # Use last n_batches for "telling" the optimizer
            parameters = parameters[-n_batches:].tolist()
            # Casting from column vector
            results = results[-n_batches:, 0].tolist()

            self.skopt_optimizer.tell(parameters, results)

        return numpy.array(
            self.skopt_optimizer.ask(n_points=n_returns)
        )
