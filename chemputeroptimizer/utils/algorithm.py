"""
Module for interfacing algorithms for optimisation.
"""

import logging
import os
import json

from collections import OrderedDict

import numpy as np

from ..algorithms import (
    Random_,
    SMBO,
    GA,
)
from .client import OptimizerClient, SERVER_SUPPORTED_ALGORITHMS


ALGORITHMS = {
    'random': Random_,
    'smbo': SMBO,
    'ga': GA,
}


class AlgorithmAPI():
    """General class to provide interface for algorithmic optimization."""

    def __init__(self):

        self.logger = logging.getLogger('optimizer.algorithm')

        # OrderedDict used to preserve the order when parsing to a np.array
        self.current_setup = OrderedDict() # current parameters setup
        self.setup_constraints = OrderedDict() # dictionary with data points constraints
        self.current_result = OrderedDict() # current result parameters
        self.parameter_matrix = None
        self.result_matrix = None
        self._calculated = None
        self.algorithm = None

        self._method_name = None
        self._method_config = None

        self.client = None
        self.proc_hash = None
        self.strategy = None

    @property
    def method_name(self):
        """Name of the selected algorithm."""
        return self._method_name

    @method_name.setter
    def method_name(self, method_name):
        if method_name not in list(ALGORITHMS) + SERVER_SUPPORTED_ALGORITHMS:
            raise KeyError(f'{method_name} is not a valid algorithm name')

        self._method_name = method_name

    @property
    def method_config(self):
        "Dictionary containing all necessary configuration for an algorithm."
        return self._method_config

    @method_config.setter
    def method_config(self, config):
        try:
            for param in config:
                assert param in ALGORITHMS[self._method_name].DEFAULT_CONFIG

        except KeyError:
            # in case algorithm is used from optimizer server
            pass

        except AssertionError:
            raise KeyError(f'{param} is not a valid parameter for \
{self._method_name}')

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
<<<<<<< HEAD
            constraints = self.setup_constraints
=======
            constraints = self.setup_constraints.values()
>>>>>>> AIL/examples

        self._load_method(
            method_name,
            config,
            constraints
        )

    def initialize(self, data):
        """First call to initialize the optimization algorithm class."""

        self.load_data(data['parameters'])
        self.proc_hash = data['hash']

        # running optimize client
        if self.method_name in SERVER_SUPPORTED_ALGORITHMS:

            # initialize client
            self.client = OptimizerClient()

            # forging initialization message
            init_msg = data.copy()
            init_msg['algorithm'] = {'name': self.method_name}
            if self.method_config:
                init_msg['algorithm'].update(self.method_config)

            # initializing
            self.client.initialize(init_msg)

        else:
            # running a local optimization algorithm
            self._load_method(
                self.method_name,
                self.method_config,
                self.setup_constraints.values()
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
            result (Dict): Nested dictionary contaning all result parameters
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

        if self.method_name in SERVER_SUPPORTED_ALGORITHMS:
            # working with remote server
            self.logger.info('Querying remote server.')
            # forging query msg
            query_data = {
                'hash': self.proc_hash,
                'parameters': self.current_setup
            }
            if self.current_result:
                query_data.update(result=self.current_result)

            self.logger.debug('Query data: %s', query_data)

            reply = self.client.query(query_data)

            # checking for exception on server side
            if 'exception' in reply:
                self.logger.exception('Exception on remote server, \
see below:\n%s', reply['exception'])
                # returning previous setup
                return self.current_setup

            # else updating
            self.strategy = reply.pop('strategy')
            self.current_setup = OrderedDict(reply)

        else:
            self._calculated = self.algorithm.suggest(
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
            header=header.rstrip(', '), # stripping the last delimiter
            comments='', # removing prepended "#"
        )

        # backing up server strategy
        if self.strategy is not None:
            file_path = os.path.join(
                os.path.dirname(path),
                'latest_strategy.json'
            )
            with open(file_path, 'w') as fobj:
                json.dump(self.strategy, fobj, indent=4)
