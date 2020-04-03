"""
Module for interfacing algorithms for optimisation.
"""

import logging

from collections import OrderedDict

import numpy as np

from ..algorithms import (
    ModifiedNelderMead,
    SNOBFIT,
    Random_,
    SMBO,
)

ALGORITHMS = {
    'nelder-mead': ModifiedNelderMead,
    'snobfit': SNOBFIT,
    'random': Random_,
    'smbo': SMBO,
}


class AlgorithmAPI():
    """General class to provide interface for algorithmic optimization.

    Arguments:
        method_name (str): Name of the chosen algorithm.
        method_config (Dict): Dictionary, containing all necessary
            attributes for the corresponding algorithm. If not given,
            default values are loaded.
    """
    def __init__(self, method_name=None, method_config=None):

        self.logger = logging.getLogger('optimizer.algorithm')

        # OrderedDict used to preserve the order when parsing to a np.array
        self.current_setup = OrderedDict() # current parameters setup
        self.setup_constraints = OrderedDict() # dictionary with data points contsraints
        self.current_result = OrderedDict() # current result parameters
        self.parameter_matrix = None
        self.result_matrix = None
        self._calculated = None
        self.algorithm = None
        # TODO wrap with @properties to check with setter method
        self.method_name = method_name
        self.method_config = method_config

    def _load_method(self, method_name, config, constraints):
        """Loads corresponding algorithm class.

        Args:
            method_name (str): Name of the chosen algorithm.
            constraints (Iterable[Iterable[float, float]]: Nested list
                of constraints, mapped by order to experimental
                parameters.
        """
        try:
            self.algorithm = ALGORITHMS[method_name](
                constraints,
                config)
        except KeyError:
            raise KeyError(f'Algorithm {method_name} not found.') from None

    def switch_method(self, method_name, config=None, constraints=None):
        """Public method for switching the algorithm."""

        if not constraints:
            constraints = self.setup_constraints

        self._load_method(
            method_name,
            config,
            constraints
        )

    def initialize(self, data):
        """First call to initialize the optimization algorithm class."""

        self.load_data(data)

        self._load_method(
            self.method_name,
            self.setup_constraints,
            self.method_config
        )

    def load_data(self, data, result=None):
        """Loads the experimental data dictionary.

        Updates:
            current_setup (OrderedDict): current parameters setup ('param', <value>)
            setup_constraints (OrderedDict): constraints of the parameters
                setup ('param', (<min_value>, <max_value>))
            current_result (OrderedDict): current results of the experiment
                ('result_param', <value>)

        Args:
            data (Dict): Nested dictionary containing all input parameters.
            result (Dict): Nested dictionary containg all result parameters
                with desired target value.

        Example:
            data = {
                    "HeatChill_1-temp": {
                        "value": 35,
                        "max": 70,
                        "min": 25,
                    }
                }

            result = {
                    "final_yield": {
                        "value": 0.75,
                        "target": 0.95,
                    }
                }
        """

        # stripping input from parameter constraints
        for param, param_set in data.items():
            self.current_setup.update({param: param_set['current_value']})

        # saving constraints
        if not self.setup_constraints:
            for param, param_set in data.items():
                self.setup_constraints.update(
                    {param: (param_set['min_value'], param_set['max_value'])})

        # appending the final result
        if result:
            self.current_result.update(result)
            # parsing data only if result was supplied
            self._parse_data()

    def _parse_data(self):
        """Parse the experimental data.

        Create the following arrays for the first experiment and add the
        subsequent data as rows:
            self.parameter_matrix: (n x i) size matrix where n is number of
                experiments and i is number of experimental parameters;
            self.result_matrix: (n x j) size matrix where j is number of the
                target parameters;

        Example:
            The experimental result:
                {"Add_1_volume": 1.5,
                "HeatChill_1_temp": 35,
                "final_yield": 0.75}

            will be dumped into the following np.arrays matrixes:
                self.parameter_matrix = np.array([1.5, 35.]);
                self.result_matrix = np.array([0.75])
        """

        # loading first value
        if self.parameter_matrix is None and self.result_matrix is None:
            # experiments as rows, data points as columns
            self.parameter_matrix = np.array(
                list(self.current_setup.values()),
                ndmin=2)
            self.result_matrix = np.array(
                list(self.current_result.values()),
                ndmin=2)

        # stacking with previous results
        else:
            self.parameter_matrix = np.vstack(
                (
                    self.parameter_matrix,
                    list(self.current_setup.values())
                )
            )

            if self._calculated is not None:
                assert (self.parameter_matrix[-1] == self._calculated).all()

            self.result_matrix = np.vstack(
                (
                    self.result_matrix,
                    list(self.current_result.values())
                )
            )

    def _remap_data(self, data_set):
        """Maps the data with the parameters."""

        self.current_setup = OrderedDict(
            zip(
                self.current_setup,
                data_set
            )
        )

    def get_next_setup(self):
        """Finds the next parameters set based on the experimental data"""

        self.logger.info('Optimizing parameters.')

        self._calculated = self.algorithm.optimize(
            self.parameter_matrix,
            self.result_matrix,
            self.setup_constraints.values()
        )

        self.logger.info(
            'Finished optimization, new parameters list in log file.')
        self.logger.debug('Parameters array: %s', list(self._calculated))

        # updating the current setup attribute
        self._remap_data(self._calculated)

        return self.current_setup

    def save(self, path):
        """Saving full experiment matrix as csv table"""

        full_matrix = np.hstack((self.parameter_matrix, self.result_matrix))

        header = ''

        for key in self.current_setup:
            header += f'{key}, '

        for key in self.current_result:
            header += f'{key}, '

        np.savetxt(
            path,
            full_matrix,
            fmt='%.04f',
            delimiter=',',
            header=header,
        )
