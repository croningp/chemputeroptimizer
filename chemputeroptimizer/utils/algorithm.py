"""
Module for interfacing algorithms for optimisation.
"""

import logging
import os
import json

from copy import deepcopy
from typing import Dict, Tuple, Optional, List, Any, Iterable

import numpy as np

from ..algorithms import (
    Random_,
    SMBO,
    GA,
    DOE,
    FromCSV,
    AbstractAlgorithm,
    Reproduce,
)
from .client import OptimizerClient, SERVER_SUPPORTED_ALGORITHMS
from .errors import NoDataError


ALGORITHMS = {
    'random': Random_,
    'smbo': SMBO,
    'ga': GA,
    'doe': DOE,
    'reproduce': Reproduce,
    'fromcsv': FromCSV,
}

# Algorithms that should not be reinstantiated
# To keep track of parameters
# Used for novelty search, see details in the corresponding method
NON_REINITIALIZED_ALGORITHMS = [
    'random',
    'fromcsv',
    'reproduce',
]

DEFAULT_RNG_SEED = 43


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

        # To run the control experiment
        self.control: bool = False  # Flag to know experiment is a control one
        self.control_options: Dict[str, int] = None
        self.control_experiment_idx: Dict[str, int] = {}
        self.iterations: int = 0  # Counting the number of performed experiments

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

        self.preload = True
        self.method_name = method_name

    def initialize(self, data, control=None):
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

            self.logger.debug('Init msg: %s', init_msg)
            # initializing and recording strategy
            self.strategy = self.client.initialize(init_msg)

        else:
            # running a local optimization algorithm
            self._load_method(
                method_name=self.method_name,
                config=self.method_config,
                constraints=self.setup_constraints.values()
            )

        if control is not None:
            self.control_options = control

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

        # Special treatment of the control experiment results
        # Those are not added to the final table of parameters/results
        # And saved separately
        if self.control:
            # Additional validation here
            self.validate_control_experiment(result)
            # Reset the flag
            self.control = False
            # Do nothing else
            return

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

        # Special case: dealing with novelty search
        # For which the results for all previous experiments
        # Should be updated with each experiment
        if result is not None and 'novelty' in result['batch 1']:
            # Due to the way novelty search works, each "batch_id" in the
            # result dictionary contains the information about all previously
            # stored data + the current batch. Thus, the last executed batch
            # will contain the data about all batches + all previously stored
            # data.

            # Tracking for the largest batch dataset
            result_dataset_sizes = []

            try:
                for batch_id in result:
                    result_dataset_sizes.append(
                        np.array(result[batch_id]['novelty'], ndmin=2).T
                    )

                    # Rewriting the result to contain only the current result
                    result[batch_id]['novelty'] = \
                        result[batch_id]['novelty'].pop(-1)

                # Sorting by the dataset size
                # The latest batch, that contains the data for all batches and
                # all previous experiments will be last and used to update the
                # result matrix.
                result_dataset_sizes.sort(key=lambda item: item.size)

                # Updating the result matrix if algorithm's returned
                # recalculated values for previous experiments, i.e. if those
                # were loaded with previous data.
                if (self.result_matrix is not None
                    and self.result_matrix.size <
                    result_dataset_sizes[-1].size
                    and self.method_name not in NON_REINITIALIZED_ALGORITHMS):
                    # Setting the result to the largest dataset, cutting the
                    # last results that correspond to the batch size
                    self.result_matrix = \
                        result_dataset_sizes[-1][:-len(result), :]

                    # In addition, reset the algorithm
                    self.switch_method(self.method_name, self.method_config)

                    # And set the preload flag
                    # So that all previous result are used
                    self.preload = True

            except (TypeError, AttributeError):
                # Happens only if the novelty result is float, i.e.
                # When preloading the results from the previous experiments
                pass

        # appending the final result
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
                try:
                    results.append(
                        list(self.current_result[batch_id].values()))
                    parameters.append(
                        list(self.current_setup[batch_id].values()))
                except KeyError:
                    # Happens when preloading results
                    # and only 1 batch is present
                    break

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
                try:
                    results.append(
                        list(self.current_result[batch_id].values()))
                    parameters.append(
                        list(self.current_setup[batch_id].values()))
                except KeyError:
                    # Happens when preloading results
                    # and only 1 batch is present
                    break

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

    def get_next_setup(
        self,
        n_batches: Optional[int] = None,
    ):
        """Finds the next parameters set based on the experimental data.

        Args:
            n_batches (Optional, int): Number of latest experiments (batches)
                and, as a consequence, number of new parameter sets to return.
                If preload parameter is set, will load all experimental data,
                but only output "n_batches" new setups. If omitted, will
                inherit the number of batches from the current setup.
        """

        self.logger.info('Optimizing parameters.')

        # Since every new iteration calls next setup
        # Counting number of performed iterations here
        self.iterations += 1

        if n_batches is None:
            n_batches = len(self.current_setup)

        # Number of points to return from the algorithm
        # Normally equals to number of batches
        n_returns = n_batches

        # Check for control experiment needed
        if (self.control_options['n_runs'] > 0
            and self.iterations >= self.control_options['every']):
            # Reset iterations count
            self.iterations = 0
            # Setting the flag
            self.control = True
            return self.query_control_experiment(n_returns)

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
            # Extracting params dictionary if params are present
            params = dict(zip(
                    self.setup_constraints,
                    self.parameter_matrix.T.tolist()
                )) if self.parameter_matrix is not None else None
            results = dict(zip(
                    self.current_result['batch 1'],
                    self.result_matrix.T.tolist()
                )) if self.result_matrix is not None else None
            # Forging query msg
            query_data = {
                'hash': self.proc_hash,
                'parameters': params,
                'n_batches': n_batches,
                'n_returns': n_returns,
            }
            if self.current_result:
                query_data.update(result=results)

            self.logger.debug('Query data: %s', query_data)

            reply = self.client.query(query_data)

            # checking for exception on server side
            if 'exception' in reply:
                self.logger.exception('Exception on remote server, \
see below:\n%s', reply['exception'])
                # returning previous setup
                return self.current_setup

            # else updating
            # self.strategy = reply.pop('strategy')
            self.current_setup.update(reply)

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

        if self.parameter_matrix is None or self.result_matrix is None:
            raise NoDataError("Nothing to save, run the experiment first!")

        full_matrix = np.hstack((self.parameter_matrix, self.result_matrix))

        header = ''

        # Pick a header from batch 1, assuming all batches have same parameters
        # And "batch 1" is always present
        for key in self.current_setup['batch 1']:
            header += f'{key},'

        for key in self.current_result['batch 1']:
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

    def query_control_experiment(self, n_returns: int) -> Dict:
        """Return the parameters for the control experiment.

        The parameters are chosen randomly from the list of previously
        used for optimization.
        """
        # Random generator
        rng = np.random.default_rng(DEFAULT_RNG_SEED)
        # Selecting random parameters from last N runs
        control_params_ids = rng.integers(
            low=1,
            high=self.control_options['every'] + 1,  # Last N experiments
            size=n_returns,
        )
        # Saving indexes batchwise
        for batch, control_id in zip(
            self.current_setup.keys(), control_params_ids):
            self.control_experiment_idx[batch] = control_id
        # Fetching control parameters
        control_params = self.parameter_matrix[-control_params_ids]
        self.logger.info('Running control experiment.')
        self.logger.debug('Parameters selected for the control experiment: %s',
            list(control_params))
        # Packing into dictionary
        self._remap_data(control_params)

        return self.current_setup

    def validate_control_experiment(self, control_result) -> Any:
        """Validate the results of the control experiment.

        Only saves data for now
        """

        self.logger.info(
            'Validating control experiment: %.2f', control_result)

        #TODO: additional logic here
