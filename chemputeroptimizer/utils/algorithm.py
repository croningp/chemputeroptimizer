"""
Module for interfacing algorithms for optimisation.
"""

import logging
import os
import json

from typing import Dict, Tuple, Optional, List, Any, Iterable

import numpy as np

from ..algorithms import (
    Random_,
    SMBO,
    # GA,
    Reproduce,
    FromCSV,
    AbstractAlgorithm,
)
from .client import OptimizerClient, SERVER_SUPPORTED_ALGORITHMS


ALGORITHMS = {
    'random': Random_,
    'smbo': SMBO,
    # 'ga': GA,
    'reproduce': Reproduce,
    'fromcsv': FromCSV,
}


class AlgorithmAPI():
    """General class to provide interface for algorithmic optimization."""

    def __init__(self) -> None:

        self.logger = logging.getLogger('optimizer.algorithm')

        # Current parameters setup
        self.current_setup: Dict[str, Dict[str, float]] = {}
        # Dictionary with data points constraints
        self.setup_constraints: Dict[str, Tuple(float, float)] = {}
        # Current result parameters
        self.current_result: Dict[str, Dict[str, float]] = {}
        self.parameter_matrix: np.ndarray = None
        self.result_matrix: np.ndarray = None
        self._calculated:  np.ndarray = None
        self.algorithm: AbstractAlgorithm = None

        self._method_name: str = None
        self._method_config: Dict[str, Any] = None

        self.client: OptimizerClient = None
        self.proc_hash: str = None
        self.strategy: Dict = None   # TODO explicit dict typing for strategy

        # To know when algorithm is first initialized
        self.preload: bool = False

    @property
    def method_name(self) -> str:
        """Name of the selected algorithm."""
        return self._method_name

    @method_name.setter
    def method_name(self, method_name: str):
        if method_name not in list(ALGORITHMS) + SERVER_SUPPORTED_ALGORITHMS:
            raise KeyError(f'{method_name} is not a valid algorithm name')

        self._method_name = method_name

    @property
    def method_config(self) -> Dict[str, Any]:
        "Dictionary containing all necessary configuration for an algorithm."
        return self._method_config

    @method_config.setter
    def method_config(self, config: Dict[str, Any]):
        try:
            for param in config:
                assert param in ALGORITHMS[self._method_name].DEFAULT_CONFIG

        except KeyError:
            # In case algorithm is used from optimizer server
            pass

        except AssertionError:
            raise KeyError(f'{param} is not a valid parameter for \
{self._method_name}') from None

        # actually setting the configuration
        self._method_config = config

    def _load_method(
        self,
        method_name: str,
        constraints: Iterable[Tuple[float, float]],
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Loads corresponding algorithm class.

        Args:
            method_name (str): Name of the chosen algorithm.
            config (Dict[str, Any]): Configuration dictionary for the chosen
                algorithm.
            constraints (Iterable[Iterable[float, float]]: Nested list
                of constraints, mapped by order to experimental
                parameters.
        """
        try:
            self.algorithm = ALGORITHMS[method_name](
                constraints,
                config
            )
        except KeyError:
            raise KeyError(f'Algorithm {method_name} not found.') from None

    def switch_method(
        self,
        method_name: str,
        config: Optional[Dict[str, Any]] = None,
        constraints: Optional[Iterable[Tuple[float, float]]] = None
    ) -> None:
        """Public method for switching the algorithm.

        Args:
            method_name (str): Name of the chosen algorithm.
            config (Dict[str, Any]): Configuration dictionary for the chosen
                algorithm. Optional, if omitted - default is used.
            constraints (Iterable[Tuple[float, float]]: Nested list
                of constraints, mapped by order to experimental
                parameters. Optional, if omitted - previous setting is used.
        """

        if constraints is None:
            constraints = self.setup_constraints.values()

        self._load_method(
            method_name=method_name,
            constraints=constraints,
            config=config,
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
                method_name=self.method_name,
                config=self.method_config,
                constraints=self.setup_constraints.values()
            )

    def load_data(
        self,
        data: Dict[str, Dict[str, Dict[str, float]]],
        result: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> None:
        """Loads the experimental data dictionaries.

        Args:
            data (Dict[str, Dict[str, Dict[str, float]]]): Nested dictionary
                containing all input parameters, grouped by batches.
            result (Optional, Dict[str, Dict[str, float]]): Nested dictionary
                contaning all result parameters with desired target value,
                grouped by batches.

        Updates internal attributes:
            current_setup (Dict[str, Dict[str, float]]): current parameters
                setup as {'param': <value>}, grouped by batch.
            setup_constraints (Dict[str, Tuple(float, float)]): constraints of
                the parameters setup {'param': (<min_value>, <max_value>)}.
            current_result (Dict[str, float]): current results of the
                experiment {'result_param': <value>}, grouped by batch.
        """

        # Stripping input from parameter constraints
        for batch_id, batch_data in data.items():
            self.current_setup[batch_id] = {}
            for param, param_set in batch_data.items():
                self.current_setup[batch_id].update(
                    {param: param_set['current_value']}
                )

        # Saving constraints
        if not self.setup_constraints:
            # Using only first batch, assuming:
            # a) it is always present;
            # b) constraints are same across batches
            for param, param_set in data['batch 1'].items():
                self.setup_constraints.update(
                    {param: (param_set['min_value'], param_set['max_value'])})

        # Appending the final result if given
        if result is not None:
            self.current_result.update(result)
            # Parsing data only if the result was supplied
            self._parse_data()

    def _parse_data(self) -> None:
        """Parse the experimental data.

        Create the following arrays for the first experiment and add the
        subsequent data as rows:
            self.parameter_matrix: (n x i) size matrix where n is number of
                experiments (* by number of batches) and i is number of
                experimental parameters.
            self.result_matrix: (n x j) size matrix where j is number of the
                target parameters.
        """

        # Loading first value
        if self.parameter_matrix is None and self.result_matrix is None:
            parameters: List[List[float]] = []
            results: List[List[float]] = []

            # Iterating over batches
            for batch_id in self.current_setup:
                # List of lists!
                parameters.append(list(self.current_setup[batch_id].values()))
                results.append(list(self.current_result[batch_id].values()))

            # Converting to arrays
            # Experiments as rows, data points as columns
            self.parameter_matrix = np.array(parameters)
            self.result_matrix = np.array(results)

        # Stacking with previous results
        else:
            parameters: List[List[float]] = []
            results: List[List[float]] = []

            # Iterating over batches
            for batch_id in self.current_setup:
                # List of lists!
                parameters.append(list(self.current_setup[batch_id].values()))
                results.append(list(self.current_result[batch_id].values()))

            # Stacking
            self.parameter_matrix = np.vstack(
                (
                    self.parameter_matrix,
                    parameters,
                )
            )

            self.result_matrix = np.vstack(
                (
                    self.result_matrix,
                    results,
                )
            )

    def _remap_data(self, data_set: np.ndarray) -> None:
        """Maps the data with the parameters."""

        # Iterating over batches
        for (batch_id, batch_data), data \
                in zip(self.current_setup.items(), data_set):
            # Updating
            self.current_setup[batch_id] = dict(zip(batch_data, data))

    def get_next_setup(self) -> Dict[str, Dict[str, float]]:
        """Finds the next parameters set based on the experimental data.

        Number of batches is inherited from the current setup.
        """

        self.logger.info('Optimizing parameters.')

        n_batches = len(self.current_setup)

        # Number of points to return from the algorithm
        # Normally equals to number of batches
        n_returns = n_batches

        if self.preload:
            # Feeding all experimental data to algorithm
            # Usually happens if new algorithm is loaded, or
            # A number of previously run experiments needs to be loaded
            n_batches = -1
            # Resetting
            self.preload = False

        if self.method_name in SERVER_SUPPORTED_ALGORITHMS:
            # working with remote server
            self.logger.info('Querying remote server.')
            # forging query msg
            query_data = {
                'hash': self.proc_hash,
                # Dict[str, np.array]
                'parameters': dict(zip(
                    self.current_setup,
                    self.parameter_matrix.T.tolist()
                )),
                'n_batches': n_batches,
            }
            if self.current_result:
                query_data.update(
                    result=dict(zip(
                        self.current_result,
                        self.result_matrix.T.tolist()
                        ))
                )

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
            self.current_setup = dict(reply)

        else:
            self._calculated = self.algorithm.suggest(
                self.parameter_matrix,
                self.result_matrix,
                self.setup_constraints.values(),
                n_batches=n_batches,
                n_returns=n_returns,
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
            header += f'{key},'

        for key in self.current_result:
            header += f'{key},'

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
