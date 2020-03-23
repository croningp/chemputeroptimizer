"""
Module to run chemical reaction optimization.
"""

import logging

from xdl import XDL

from .platform import OptimizerPlatform
from .platform.steps import OptimizeDynamicStep, OptimizeStep
from .constants import (
    SUPPORTED_STEPS_PARAMETERS,
    DEFAULT_OPTIMIZATION_PARAMETERS,
)
from .utils.errors import OptimizerError, ParameterError
from .utils import get_logger


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
                 fake=True,
                 opt_params=None):

        self.logger = get_logger()

        self._original_procedure = procedure
        self.graph = graph_file
        self.interactive = interactive
        if opt_params is None:
            opt_params = DEFAULT_OPTIMIZATION_PARAMETERS

        self._xdl_object = XDL(procedure, platform=OptimizerPlatform)
        self.logger.debug('Initilaized xdl object (id %d).',
                          id(self._xdl_object))

        self._optimization_steps = {
        }  # in form of {'Optimization step ID': <:obj: Optimization step instance>, ...}

        self._check_optimization_steps_and_parameters(fake)

        self._initalise_optimize_step(opt_params)

    def _initalise_optimize_step(self, opt_params):
        """Initialize Optimize Dynamic step with relevant optimization parameters"""

        self.optimizer = OptimizeDynamicStep(
            original_xdl=self._xdl_object,
            save_path='here',
            optimize_steps=self._optimization_steps,
            **opt_params)
        self.logger.debug('Initialized Optimize dynamic step.')

    def _check_optimization_steps_and_parameters(self, fake):
        """Get the optimization parameters and validate them if needed"""

        optimize_steps = []
        self.logger.debug('Probing for OptimizeStep steps in xdl object.')

        for step in self._xdl_object.steps:
            if step.name == 'OptimizeStep':
                optimize_steps.append(step)
                if step.children[0] not in SUPPORTED_STEPS_PARAMETERS:
                    raise OptimizerError(
                        f'Step {step} is not supported for optimization')

                for parameter in step.optimize_properties:
                    if parameter not in SUPPORTED_STEPS_PARAMETERS[step]:
                        raise ParameterError(
                            f'Parameter {parameter} is not supported for step {step}'
                        )

        if not optimize_steps and not fake:
            self.logger.debug('OptimizeStep steps were not found, creating.')
            for i, step in enumerate(self._xdl_object.steps):
                if step.name in SUPPORTED_STEPS_PARAMETERS:
                    self._xdl_object.steps[i] = self._create_optimize_step(
                        step, i)

        if not optimize_steps and fake:
            self.logger.debug(
                'OptimizeStep steps were not found, creating fake steps.')
            for i, step in enumerate(self._xdl_object.steps):
                if step.name in SUPPORTED_STEPS_PARAMETERS:
                    self._optimization_steps.update({
                        f'{step.name}_{i}':
                        self._create_optimize_step(step, i)
                    })

    def _create_optimize_step(self, step, step_id):
        """Creates an OptimizeStep from supplied xdl step
        
        Args:
            step (Step): XDL step to be wrapped with OptimizeStep,
                must be supported
        
        Returns:
            dict: dictionary with OptimizeStepID as a key and OptimizeStep instance
                as value.
        """

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
            'Created OptimizeStep for <%s> with following parameters %s',
            step.name, params)

        return optimize_step

    def prepare_for_optimization(self, interactive=False):
        """Get the Optimize step and the respective parameters"""

        self.optimizer.prepare_for_execution(self.graph,
                                             self._xdl_object.executor)

    def optimize(self, chempiler):
        """Execute the Optimize step and follow the optimization routine"""

        #self.optimizer.execute(chempiler)
