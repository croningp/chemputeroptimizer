"""
Module to run chemical reaction optimization.
"""

# std lib
import json
from pathlib import Path
from typing import Dict, Any
from copy import deepcopy
from csv import reader as csv_reader

# xdl
from xdl import XDL

# chempiler
from chempiler.tools.graph import load_graph

# relative
from .platform import OptimizerPlatform
from .platform.steps import (
    OptimizeDynamicStep,
    Analyze,
)
from .platform.steps.utils import (
    extract_optimization_params,
)
from .constants import (
    SUPPORTED_STEPS_PARAMETERS,
    DEFAULT_OPTIMIZATION_PARAMETERS,
    BATCH_1,
)
from .utils.errors import (
    OptimizerError,
    ParameterError,
    OptimizerNotPreparedError,
)
from .utils import (
    get_logger,
    interactive_optimization_config,
    interactive_optimization_steps,
    AlgorithmAPI,
    create_optimize_step,
)
# Optimizer Client specific
from .utils.client import (
    proc_data,
    calculate_procedure_hash,
)
from .utils.validation import (
    validate_algorithm,
    validate_algorithm_batch_size,
    find_and_validate_optimize_steps,
    validate_optimization_config,
    update_configuration,
)


class ChemputerOptimizer():
    """
    Main class to run the chemical reaction optimization.

    Instantiates XDL object to load the experimental procedure,
    validate it against the given graph and place all implied steps required
    to run the procedure.

    Attributes:
        procedure (str): Path to XDL file or XDL str.
        graph_file (str): Path to graph file (either .json or .graphml).
        interactive (bool, optional): User input for OptimizeStep parameters.
        opt_params (str, optional): Path to .json config file contaning
            steps to optimize.
    """
    def __init__(
            self,
            procedure: str,
            graph_file: str,
            interactive: bool = False,
        ):

        self.logger = get_logger()

        self._original_procedure = procedure
        self.graph = load_graph(graph_file)
        self.interactive = interactive

        self.algorithm = AlgorithmAPI()

        self._xdl_object = XDL(procedure, platform=OptimizerPlatform)

        # Check for necessary optimization steps
        # Or insert missing if needed
        self._check_final_analysis_steps()
        self._check_optimization_steps_and_parameters()

        self.logger.debug('Initialized xdl object (id %d).',
                          id(self._xdl_object))

        self._initialize_optimize_step()

        # placeholder
        self.prepared = False

    def _check_final_analysis_steps(self) -> None:
        """Checks for FinalAnalysis steps in the procedure

        If no steps found - issue is raised. If running in interactive mode
        will add an interactive FinalAnalysis method at the end of the
        procedure.

        Raises:
            OptimizerError: If no FinalAnalysis found and ChemputerOptimizer
                is instantiated in non-interactive mode.
        """

        final_analysis_steps = []

        for i, step in enumerate(self._xdl_object.steps):
            if step.name == 'FinalAnalysis' or step.name == 'Analyze':
                # Building reference step dictionary
                reference_step_name = self._xdl_object.steps[i - 1].name
                if reference_step_name == 'OptimizeStep':
                    # Stripping to the children step
                    reference_step = self._xdl_object.steps[i - 1].children[0]
                else:
                    reference_step = self._xdl_object.steps[i - 1]

                # Reference step is used to allow additional preparations
                # To execute the analysis
                # For example cooling down, filtering, evaporating, etc.
                step.reference_step = {
                    'step': reference_step.name,
                    'properties': {
                        prop: value
                        for prop, value
                        in reference_step.properties.items()
                        # Don't save context property
                        # As its not JSON serializable
                        if 'context' not in prop
                    }
                }
                final_analysis_steps.append(step)

        # Raise an error if no analysis steps found
        # And running in non-interactive mode
        if not final_analysis_steps and not self.interactive:
            raise OptimizerError('No FinalAnalysis steps found, please \
add them to the procedure or run ChemputerOptimizer in interactive mode.')

        # If no steps found, but running in interactive mode
        # Append an interactive Analyze step at the end
        if not final_analysis_steps and self.interactive:
            self.logger.info('No FinalAnalysis steps found, appending one \
at the end of the procedure with an interactive method.')

            self._xdl_object.steps.append(
                Analyze(
                    vessel=None,
                    method='interactive',
                    reference_step=None,
                )
            )

    def _initialize_optimize_step(self) -> None:
        """Initialize Optimize Dynamic step with relevant optimization
            parameters"""

        self.optimizer = OptimizeDynamicStep(
            original_xdl=self._xdl_object,
            algorithm_class=self.algorithm,
            )
        self.logger.debug('Initialized Optimize dynamic step.')

    def _check_optimization_steps_and_parameters(self) -> None:
        """Get the optimization parameters and validate them if needed.

        Raises:
            OptimizerError: If the step for the optimization is not supported.
            ParameterError: If invalid parameter selected for the step to
                optimize.
        """

        self.logger.debug('Probing for OptimizeStep steps in xdl object.')

        # Looking for optimization steps
        optimize_steps = find_and_validate_optimize_steps(
            procedure=self._xdl_object,
            logger=self.logger,
        )

        # If no steps found - create them
        if not optimize_steps:
            self.logger.info('OptimizeStep steps were not found, creating.')
            for i, step in enumerate(self._xdl_object.steps):
                # Looking for steps "suitable" for optimization
                if step.name in SUPPORTED_STEPS_PARAMETERS:
                    # Placeholder for OptimizeStep parameters
                    params = None
                    if self.interactive:
                        # Prompt user for parameters for the OptimizeSteps
                        params = interactive_optimization_steps(step, i)
                        # Skip, if no parameters returned
                        if not params:
                            continue

                    # Now create an OptimizeStep at the position of ith step
                    self._xdl_object.steps[i] = create_optimize_step(
                        step=step,
                        step_id=i,
                        params=params,
                        logger=self.logger,
                    )

    def prepare_for_optimization(
            self,
            opt_params=None,
            previous_results=None,
    ) -> None:
        """Get the Optimize step and the respective parameters

        Args:
            opt_params (str, Optional): Path to .json configuration. If omitted,
                will use default. If running in interactive mode, will ask for
                user input.
            previous_results (str, Optional): Path to .csv file with previous
                results. If given, will update the algorithm class and the
                given xdl.

        Raises:
            OptimizerError: If invalid dictionary is provided for to load
                configuration or invalid path to .json configuration.
            ParameterError: If supplied parameter is not valid for the
                optimization.
        """

        # Do not prepare twice!
        if self.prepared:
            self.logger.warning('Already prepared!')
            return

        # Build optimization config with user input
        if self.interactive:
            opt_params = interactive_optimization_config()

        # OR read config from json file
        elif isinstance(opt_params, str):
            try:
                with open(opt_params, 'r') as f:
                    self.logger.debug('Loading json configuration from %s',
                                  opt_params)
                    opt_params = json.load(f)
            except FileNotFoundError:
                raise OptimizerError('Please provide a valid optimization \
configuration file.') from None

        # OR load default configuration
        else:
            opt_params = deepcopy(DEFAULT_OPTIMIZATION_PARAMETERS)

        # Valide the input
        validate_optimization_config(config=opt_params)

        # Loading missing default parameters
        update_configuration(opt_params, DEFAULT_OPTIMIZATION_PARAMETERS)

        # saving updated config if running in interactive mode
        if self.interactive:
            here = Path(self._original_procedure).parent
            json_file = here.joinpath('optimizer_config.json')
            with open(json_file, 'w') as f:
                json.dump(opt_params, f, indent=4)

        # updating algorithmAPI
        algorithm_parameters = opt_params.pop('algorithm')
        algorithm_name = algorithm_parameters.pop('name')
        # Validation
        validate_algorithm(algorithm_name)
        procedure_hash = calculate_procedure_hash(self._xdl_object.as_string())
        procedure_parameters = extract_optimization_params(self._xdl_object, 1)
        procedure_target = opt_params['target']
        batch_size = opt_params['batch_size']
        control = opt_params['control']
        # Validation
        validate_algorithm_batch_size(algorithm_name, batch_size)

        self.initialize_algorithm(
            algorithm_name=algorithm_name,
            algorithm_config=algorithm_parameters,
            proc_hash=procedure_hash,
            proc_params=procedure_parameters,
            proc_target=procedure_target,
            batch_size=batch_size,
            control=control,
        )

        self.logger.info('Loaded the following parameter dict %s', opt_params)
        self.logger.info('Loaded the %s algorithm with the following \
parameters : %s', algorithm_name, algorithm_parameters)

        self.optimizer.load_optimization_config(**opt_params)
        self.optimizer.on_prepare_for_execution(self.graph)
        self.optimizer.prepare_for_execution(self.graph,
                                             self._xdl_object.executor,)

        self.prepared = True

        if previous_results is not None:
            self.load_previous_results(results=previous_results)

    def optimize(self, chempiler):
        """Execute the Optimize step and follow the optimization routine"""

        self.optimizer.execute(chempiler)

    def initialize_algorithm(
        self,
        algorithm_name: str,
        algorithm_config: Dict[str, Any],
        proc_hash: str,
        proc_params: Dict[str, Dict[str, Any]],
        proc_target: Dict[str, Any],
        batch_size: int,
        control: Dict[str, int],
    ) -> None:
        """Initialize the AlgorithmAPI and underlying algorithm class.

        Load the algorithm name and configuration. Initialize the underlying
        algorithm class with procedure parameters and target.

        Args:
            algorithm_name (str): Name of the optimization algorithm.
            algorithm_config (Dict[str, Any]): Configuration dictionary for the
                optimization algorithm.
            proc_hash (str): Digest of a procedure hash calculated using sha256
                algorithm, as a string of hexadecimal digits. Used with
                Optimizer Client to match identical procedures for parallel
                optimization.
            proc_params (Dict[str, Dict[str, Any]]): Nested dictionary with
                parameters keys and values as their constraints.
            proc_target (Dict[str, Any]): Dictionary with the target parameters
                for the given procedure.
            batch_size (int): Number of parallel optimizations to perform. Must
                be consistent with number of available hardware modules, as
                no additional checks are performed.
            control (Dict[str, int]): Parameters to run the control experiment.
        """
        # Updating placeholders
        self.algorithm.method_name = algorithm_name
        self.algorithm.method_config = algorithm_config

        # Initialing the optimization algorithm
        # Special function (proc_data) to forge nested dictionary
        # Used for Optimizer Client
        self.algorithm.initialize(proc_data(
                proc_hash=proc_hash,
                parameters=proc_params,
                target=proc_target,
                batch_size=batch_size
            ),
            control=control,
        )

    def load_previous_results(self,
                              results: str, update_xdl: bool = True) -> None:
        """ Loads previous results and updates the current working xdl.

        Args:
            results (str): Path to .csv file with the results from the previous
                iterations. Should contain first row as names of the procedure
                parameters.
            update_xdl (bool): If true will update the loaded xdl.
        """
        if not self.prepared:
            raise OptimizerNotPreparedError('Optimizer not prepared! Please \
run "prepare_for_optimization" method first.')

        try:
            with open(results, newline='') as results_fobj:
                results = list(csv_reader(results_fobj))
        except FileNotFoundError:
            raise FileNotFoundError(
                f'Ensure file {results} exists!') from None

        # checking for entries
        try:
            assert(
                set(results[0][:-1]) == set(self.algorithm.setup_constraints))

        except AssertionError:
            raise ParameterError(
                'Wrong parameters found in results file:\n{}. Must \
contain:\n{}'.format(set(results[0]), set(self.algorithm.setup_constraints))
                ) from None

        for row in results[1:]: # skipping header row
            # converting
            # dropping last column as result
            #TODO change here when deal with multiobjective optimization
            data = {
                key: {'current_value': float(value)}
                for key, value in zip(results[0][:-1], row[:-1])
            }
            result = {
                results[0][-1]: float(row[-1])
            }
            # Wrapping everything in a "single batch" data
            data = {BATCH_1: data}
            result = {BATCH_1: result}
            # Now loading to the algorithm
            self.algorithm.load_data(data=data, result=result)

        # Setting the flag to load all data into algorithm
        self.algorithm.preload = True

        # when data is loaded, update the xdl
        if update_xdl:
            self.optimizer.update_steps_parameters()
