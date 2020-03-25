"""
Module to run chemical reaction optimization.
"""

import logging
import json

from xdl import XDL

from .platform import OptimizerPlatform
from .platform.steps import OptimizeDynamicStep, OptimizeStep
from .constants import (
    SUPPORTED_STEPS_PARAMETERS,
    DEFAULT_OPTIMIZATION_PARAMETERS,
)
from .utils.errors import OptimizerError, ParameterError
from .utils import (get_logger, interactive_optimization_config)


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
        fake (bool, optional): If the fake OptimizeSteps created.
        opt_params (Dict, optional): Dictionary with optimization parameters,
            e.g. number of iterations, optimization algorithm, target parameter
            and its value.
    """
    def __init__(self,
                 procedure,
                 graph_file,
                 interactive=False,
                 optimize_steps=None):

        self.logger = get_logger()

        self._original_procedure = procedure
        self.graph = graph_file
        self.interactive = interactive

        self._xdl_object = XDL(procedure, platform=OptimizerPlatform)
        self.logger.debug('Initilaized xdl object (id %d).',
                          id(self._xdl_object))

        if optimize_steps and isinstance(optimize_steps, str):
            self.logger.debug('Found optimization steps config file %s, \
loading.', optimize_steps)
            try:
                self._optimization_steps = self._load_optimization_steps(optimize_steps)
            except FileNotFoundError:
                raise FileNotFoundError(f'File "{optimize_steps}" not found!') from None
        else:
            self._optimization_steps = {}

        self._check_optimization_steps_and_parameters()

        self._initalise_optimize_step()

    def _initalise_optimize_step(self):
        """Initialize Optimize Dynamic step with relevant optimization parameters"""

        self.optimizer = OptimizeDynamicStep(
            original_xdl=self._xdl_object,
            )
        self.logger.debug('Initialized Optimize dynamic step.')

    def _load_optimization_steps(self, file):
        """Loads optimization steps from .json config file"""
        with open(file, 'r') as f:
            optimization_steps = json.load(f)

        # check for consistency vs xdl procedure
        for step_id in optimization_steps:
            # unpacking step data from "Step_ID"
            step, sid = step_id.split('_')

            if step != self._xdl_object.steps[int(sid)].name:
                raise OptimizerError(f'Step "{step}" does not match original procedure \
at position {sid}, procedure.steps[{sid}] is {self._xdl_object.steps[int(sid)].name}.')

        return optimization_steps

    def _check_optimization_steps_and_parameters(self):
        """Get the optimization parameters and validate them if needed"""

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
                    self._optimization_steps[optimization_step]
                )

        if not self._optimization_steps:
            self.logger.debug('OptimizeStep steps were not found, creating.')
            for i, step in enumerate(self._xdl_object.steps):
                if step.name in SUPPORTED_STEPS_PARAMETERS:
                    self._xdl_object.steps[i] = self._create_optimize_step(
                        step, i)

    def _create_optimize_step(self, step, step_id, params=None):
        """Creates an OptimizeStep from supplied xdl step

        Args:
            step (Step): XDL step to be wrapped with OptimizeStep,
                must be supported

        Returns:
            dict: dictionary with OptimizeStepID as a key and OptimizeStep instance
                as value.
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

    def prepare_for_optimization(self, opt_params=None, **kwargs):
        """Get the Optimize step and the respective parameters"""

        if self.interactive:
            opt_params = interactive_optimization_config()

        elif isinstance(opt_params, str):
            if '.json' in opt_params:
                self.logger.debug('Loading json configuration from %s', opt_params)
                with open(opt_params, 'r') as f:
                    opt_params = json.load(f)
            else:
                raise OptimizerError('Parameters must be .json file!')

        elif opt_params is not None and not isinstance(opt_params, dict):
            raise OptimizerError('Parameters must be dictionary!')

        elif opt_params is None and kwargs:
            opt_params = {}
            for k, v in kwargs.items():
                opt_params[k] = v

        else:
            opt_params = DEFAULT_OPTIMIZATION_PARAMETERS

        for k, v in opt_params.items():
            if k not in DEFAULT_OPTIMIZATION_PARAMETERS:
                raise OptimizerError(f'<{k}> not a valid optimization parameter!')

        # loading missing default parameters
        for k, v in DEFAULT_OPTIMIZATION_PARAMETERS.items():
            if k not in opt_params:
                opt_params[k] = v

        self.logger.debug('Loaded the following parameter dict %s', opt_params)

        self.optimizer.load_config(**opt_params)
        self.optimizer.prepare_for_execution(self.graph,
                                             self._xdl_object.executor)

    def optimize(self, chempiler):
        """Execute the Optimize step and follow the optimization routine"""

        #self.optimizer.execute(chempiler)
