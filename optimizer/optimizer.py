"""
Module to run chemical reaction optimization.
"""

import logging

from xdl import XDL

from .platform import OptimizerPlatform
from .platform.steps import Optimize, OptimizeStep
from .constants import (SUPPORTED_STEPS_PARAMETERS)
from .utils.errors import OptimizerError, ParameterError

class Optimizer(object):
    """
    Main class to run the chemical reaction optimization.

    Instantiates XDL object to load the experimental procedure,
    validate it against the given graph and place all implied steps required
    to run the procedure.

    Attributes:
        procedure (str): Path to XDL file or XDL str.
        graph_file (str): Path to graph file (either .json or .graphml)
    """

    def __init__(self, procedure, graph_file):

        self._original_procedure = procedure
        self.graph = graph_file

        self.optimizer = None

        self.platform = OptimizerPlatform

        self._xdl_object = XDL(procedure, platform=self.platform)

        self._original_steps = self._xdl_object.steps

        self._optimization_steps = {} # in form of {'Optimization step ID': <:obj: Optimization step instance>, ...}

        self.logger = logging.getLogger('optimizer')

        self._fetch_optimize_steps()

    def _fetch_optimize_steps(self):
        """Fetches all OptimizeStep steps if present"""

        for i, step in enumerate(self._xdl_object.steps):
            if step.name == 'OptimizeStep':
                self._optimization_steps.update(
                    {
                        f'{step.children[0].name}_{i}': step.optimize_properties
                    }
                )

    def _check_otpimization_steps_and_parameters(self):
        """Get the optimization parameters and validate them if needed"""

        if not self._optimization_steps:
            for step in self._optimization_steps:
                if step not in SUPPORTED_STEPS_PARAMETERS:
                    raise OptimizerError(f'Step {step} is not supported for optimization')

                for parameter in self._optimization_steps[step]:
                    if parameter not in SUPPORTED_STEPS_PARAMETERS[step]:
                        raise ParameterError(f'Parameter {parameter} is not supported for step {step}')

    def _get_optimization_steps(self, interactive=False):
        """Get the optimization steps from the given procedure"""

        if self._optimization_steps and not interactive:
            return

        if not self._optimization_steps:
            for i, step in enumerate(self._xdl_object.steps):
                if step.name in SUPPORTED_STEPS_PARAMETERS:
                    self._optimization_steps.update(self._create_optimize_step(step, i))

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
            } for param in SUPPORTED_STEPS_PARAMETERS[step.name]
            if step.properties[param] is not None
        }

        optimize_step = OptimizeStep(
            id=str(step_id),
            children=[step],
            optimize_properties=params,
        )

        return {f'{step.name}_{step_id}': optimize_step}

    def prepare_for_optimization(self, interactive=False):
        """Get the Optimize step and the respective parameters"""

        self._get_optimization_steps(interactive=interactive)

        self.optimizer = Optimize(
            xdl_object=self._xdl_object,
            max_iterations=1,
            target={'final_yield': 0.95},
            save_path='here',
            optimize_steps=self._optimization_steps,
        )

    def optimize(self, chempiler):
        """Execute the Optimize step and follow the optimization routine"""

        #self.optimizer.execute(chempiler)
