"""
Module to run chemical reaction optimization.
"""

import logging
import json
import os

from typing import Dict, Union
from copy import deepcopy

import AnalyticalLabware

from xdl import XDL
from xdl.steps import Step

from .platform import OptimizerPlatform
from .platform.steps import (
    OptimizeDynamicStep,
    OptimizeStep,
    FinalAnalysis,
)
from .platform.steps.utils import (
    find_last_meaningful_step,
)
from .constants import (
    SUPPORTED_STEPS_PARAMETERS,
    DEFAULT_OPTIMIZATION_PARAMETERS,
    SUPPORTED_FINAL_ANALYSIS_STEPS,
)
from .utils.errors import OptimizerError, ParameterError
from .utils import (
    get_logger,
    interactive_optimization_config,
    interactive_optimization_steps,
    AlgorithmAPI,
)


class ChemputerOptimizer(object):
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

        self._initalise_optimize_step()

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
                step.reference_step = self._xdl_object.steps[i - 1]
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

            self._xdl_object.steps.insert(
                position,
                FinalAnalysis(
                    vessel=last_meaningful_step.vessel,
                    method='interactive',
                    reference_step=last_meaningful_step,
                )
            )

    def _initalise_optimize_step(self) -> None:
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

        # checking procedure for consistency
        for step in self._xdl_object.steps:
            if step.name == 'OptimizeStep':
                if step.children[0] not in SUPPORTED_STEPS_PARAMETERS:
                    raise OptimizerError(
                        f'Step {step} is not supported for optimization')

                for parameter in step.optimize_properties:
                    if parameter not in SUPPORTED_STEPS_PARAMETERS[step]:
                        raise ParameterError(
                            f'Parameter {parameter} is not supported for step {step}'
                        )

        if self._optimization_steps:
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
                    self._optimization_steps.update({f'{step.name}_{i}': f'{params}'})

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
    ) -> None:
        """Get the Optimize step and the respective parameters

        Args:
            opt_params (str, Optional): Path to .json configuration. If omitted,
                will use default. If running in interactive mode, will ask for user input.

        Raises:
            OptimizerError: If invalid dictionary is provided for to load configuration
                or invalid path to .json configuration.
            ParameterError: If supplied parameter is not valid for the optimization.
        """

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
        self.algorithm.method_name = algorithm_name
        self.algorithm.method_config = algorithm_parameters

        self.logger.debug('Loaded the following parameter dict %s', opt_params)

        self.optimizer.load_optimization_config(**opt_params)
        self.optimizer.prepare_for_execution(self.graph,
                                             self._xdl_object.executor,)

    def optimize(self, chempiler):
        """Execute the Optimize step and follow the optimization routine"""

        self.optimizer.execute(chempiler)
