"""
Module to run chemical reaction optimization.
"""

# std lib
import json
import os
from typing import Dict, Any
from copy import deepcopy
from csv import reader as csv_reader

# xdl
from xdl import XDL
from xdl.steps import Step

# relative
from .platform import OptimizerPlatform
from .platform.steps import (
    OptimizeDynamicStep,
    OptimizeStep,
    FinalAnalysis,
)
from .platform.steps.utils import (
    find_last_meaningful_step,
    extract_optimization_params,
)
from .constants import (
    SUPPORTED_STEPS_PARAMETERS,
    DEFAULT_OPTIMIZATION_PARAMETERS,
    SUPPORTED_FINAL_ANALYSIS_STEPS,
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
)
# Optimizer Client specific
from .utils.client import (
    proc_data,
    calculate_procedure_hash,
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
            optimize_steps: str = None,
            interactive: bool = False,
        ):

        self.logger = get_logger()

        self._original_procedure = procedure
        self.graph = graph_file
        self.interactive = interactive

        self.algorithm = AlgorithmAPI()

        self._xdl_object = XDL(procedure, platform=OptimizerPlatform)
        self._check_final_analysis_steps()
        self.logger.debug('Initialized xdl object (id %d).',
                          id(self._xdl_object))

        if optimize_steps and isinstance(optimize_steps, str):
            self.logger.debug(
                'Found optimization steps config file %s, \
loading.', optimize_steps)
            try:
                self._optimization_steps = self._load_optimization_steps(
                    optimize_steps)
            except FileNotFoundError:
                raise FileNotFoundError(
                    f'File "{optimize_steps}" not found!') from None
        else:
            self._optimization_steps = {}

        self._check_optimization_steps_and_parameters()

        if not self._optimization_steps:
            # TODO public methods for loading optimization steps
            raise OptimizerError('No OptimizeSteps found or given!')

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
            if step.name == 'FinalAnalysis':
                # building reference step dictionary
                reference_step = {
                    'step': self._xdl_object.steps[i - 1].name,
                    'properties': self._xdl_object.steps[i - 1].properties,
                }
                step.reference_step = reference_step
                final_analysis_steps.append(step)

        if not final_analysis_steps and not self.interactive:
            raise OptimizerError('No FinalAnalysis steps found, please \
add them to the procedure or run ChemputerOptimizer in interactive mode.')

        if not final_analysis_steps and self.interactive:
            position, last_meaningful_step = find_last_meaningful_step(
                self._xdl_object.steps,
                SUPPORTED_FINAL_ANALYSIS_STEPS,
            )

            self.logger.info('No FinalAnalysis steps found, will insert one \
after the last %s step in the procedure (at position %s) with an interactive \
method', last_meaningful_step.name, position)

            last_meaningful_step = {
                'step': last_meaningful_step.name,
                'properties': last_meaningful_step.properties,
            }

            self._xdl_object.steps.insert(
                position,
                FinalAnalysis(
                    vessel=last_meaningful_step['properties']['vessel'],
                    method='interactive',
                    reference_step=last_meaningful_step,
                )
            )

    def _initialize_optimize_step(self) -> None:
        """Initialize Optimize Dynamic step with relevant optimization parameters"""

        self.optimizer = OptimizeDynamicStep(
            original_xdl=self._xdl_object,
            algorithm_class=self.algorithm,
            )
        self.logger.debug('Initialized Optimize dynamic step.')

    def _load_optimization_steps(self, file: str) -> Dict:
        """Loads optimization steps from .json config file

        Args:
            file (str): Path to .json configuration for steps to Optimize,
                see examples in /tests/config/
        Returns:
            Dict: Dictionary of steps to Optimize, following pattern -
                {'StepName_StepID':
                    {'param':
                        {'min_value': value,
                         'max_value': value,
                        }
                    }
                }

        Raises:
            OptimizerError: If the 'StepName_StepID' pattern doesn't match
                the original xdl procedure.
        """

        with open(file, 'r') as f:
            optimization_steps = json.load(f)

        # check for consistency vs xdl procedure
        for step_id in optimization_steps:
            # unpacking step data from "Step_ID"
            step, sid = step_id.split('_')

            if step != self._xdl_object.steps[int(sid)].name:
                raise OptimizerError(
                    f'Step "{step}" does not match original procedure \
at position {sid}, procedure.steps[{sid}] is {self._xdl_object.steps[int(sid)].name}.'
                )

        return optimization_steps

    def _check_optimization_steps_and_parameters(self) -> None:
        """Get the optimization parameters and validate them if needed.

        Raises:
            OptimizerError: If the step for the optimization is not supported.
            ParameterError: If invalid parameter selected for the step to
                optimize.
        """

        self.logger.debug('Probing for OptimizeStep steps in xdl object.')

        # internal tag to avoid step unnecessary step creation
        consistent = False

        # checking procedure for consistency
        for step in self._xdl_object.steps:
            if step.name == 'OptimizeStep':
                optimized_step = step.children[0].name
                if optimized_step not in SUPPORTED_STEPS_PARAMETERS:
                    raise OptimizerError(
                        f'Step {optimized_step} is not supported for optimization')

                for parameter in step.optimize_properties:
                    if parameter not in SUPPORTED_STEPS_PARAMETERS[optimized_step]:
                        raise ParameterError(
                            f'Parameter {parameter} is not supported for step {step}'
                        )
                self._optimization_steps.update(
                    {f'{optimized_step}_{step.id}': f'{step.optimize_properties}'}
                )
                self.logger.debug('Found OptimizeStep for %s.', optimized_step)
                consistent = True

        # creating steps only if no OptimizeStep found in the procedure
        if self._optimization_steps and not consistent:
            for optimization_step in self._optimization_steps:
                # unpacking step data from "Step_ID"
                step, sid = optimization_step.split('_')

                self._xdl_object.steps[int(sid)] = self._create_optimize_step(
                    self._xdl_object.steps[int(sid)],
                    int(sid),
                    self._optimization_steps[optimization_step])

        if not self._optimization_steps:
            self.logger.info('OptimizeStep steps were not found, creating.')
            for i, step in enumerate(self._xdl_object.steps):
                if step.name in SUPPORTED_STEPS_PARAMETERS:
                    params = None
                    if self.interactive:
                        params = interactive_optimization_steps(
                            step, i)
                        if not params:
                            continue

                    self._xdl_object.steps[i] = self._create_optimize_step(
                        step, i, params)
                    self._optimization_steps.update(
                        {f'{step.name}_{i}': f'{params}'})

    def _create_optimize_step(
            self,
            step: Step,
            step_id: int,
            params: Dict = None,
        ) -> Step:
        """Creates an OptimizeStep from supplied xdl step

        Args:
            step (Step): XDL step to be wrapped with OptimizeStep,
                must be supported.
            step_id (int): Ordinal number of a step.
            params (Dict, optional): Parameters for the OptimizeStep as
                nested dictionary.

        Example params:
            {'<param>': {'max_value': <value>, 'min_value': <value>}}

        Returns:
            :obj: XDL.Step: An OptimizeStep step wrapper for the
                XDL step to be optimized.
        """
        if params is None:
            params = {
                param: {
                    'max_value': float(step.properties[param]) * 1.2,
                    'min_value': float(step.properties[param]) * 0.8,
                }
                for param in SUPPORTED_STEPS_PARAMETERS[step.name]
                if step.properties[param] is not None
            }

        optimize_step = OptimizeStep(
            id=str(step_id),
            children=[step],
            optimize_properties=params,
        )

        self.logger.debug(
            'Created OptimizeStep for <%s_%d> with following parameters %s',
            step.name, step_id, params)

        return optimize_step

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

        if self.prepared:
            self.logger.warning('Already prepared!')
            return

        if self.interactive:
            opt_params = interactive_optimization_config()

        elif isinstance(opt_params, str):
            if '.json' in opt_params:
                self.logger.debug('Loading json configuration from %s',
                                  opt_params)
                with open(opt_params, 'r') as f:
                    opt_params = json.load(f)
            else:
                raise OptimizerError('Parameters must be .json file!')

        else:
            opt_params = deepcopy(DEFAULT_OPTIMIZATION_PARAMETERS)

        for k, _ in opt_params.items():
            if k not in DEFAULT_OPTIMIZATION_PARAMETERS:
                raise ParameterError(
                    f'<{k}> not a valid optimization parameter!')

        # loading missing default parameters
        for k, v in DEFAULT_OPTIMIZATION_PARAMETERS.items():
            if k not in opt_params:
                opt_params[k] = v

        # saving updated config if running in interactive mode
        if self.interactive:
            here = os.path.dirname(self._original_procedure)
            json_file = os.path.join(here, 'optimizer_config.json')
            with open(json_file, 'w') as f:
                json.dump(opt_params, f, indent=4)

        # updating algorithmAPI
        algorithm_parameters = opt_params.pop('algorithm')
        algorithm_name = algorithm_parameters.pop('name')
        procedure_hash = calculate_procedure_hash(self._xdl_object.as_string())
        procedure_parameters = {
            'batch 1': extract_optimization_params(self._xdl_object)
        }
        procedure_target = opt_params['target']
        self.initialize_algorithm(
            algorithm_name=algorithm_name,
            algorithm_config=algorithm_parameters,
            proc_hash=procedure_hash,
            proc_params=procedure_parameters,
            proc_target=procedure_target,
        )

        self.logger.debug('Loaded the following parameter dict %s', opt_params)

        self.optimizer.load_optimization_config(**opt_params)
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
        ))

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
                'Wrong parameters found in results file:\n{}. Must\
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
            data = {'batch 1': data}
            result = {'batch 1': result}
            # Now loading to the algorithm
            self.algorithm.load_data(data=data, result=result)

        # Setting the flag to load all data into algorithm
        self.algorithm.preload = True

        # when data is loaded, update the xdl
        if update_xdl:
            self.optimizer.update_steps_parameters()
