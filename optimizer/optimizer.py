"""
Module to run chemical reaction optimization.
"""

import logging

from xdl import XDL

from .steps import Optimize
from .platform import OptimizerPlatform
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

        self._xdl_object = XDL(procedure, platform=OptimizerPlatform)

        self._original_steps = self._xdl_object.steps

        self._optimization_steps = {}

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

        if not interactive:
            for i, step in enumerate(self._xdl_object.steps):
                if step.name in SUPPORTED_STEPS_PARAMETERS:
                    self._optimization_steps.update(
                        {
                            f'{step.name}_{i}': {
                                parameter: {
                                    'max_value': float(step.properties[parameter]) * 1.2,
                                    'min_value': float(step.properties[parameter]) * 0.8
                                } for parameter in SUPPORTED_STEPS_PARAMETERS[step.name]
                                if step.properties[parameter] is not None
                            }
                        }
                    )

    def prepare_for_optimization(self, interactive=False):
        """Get the Optimize step and the respective parameters"""

        self._get_optimization_steps(interactive=interactive)

    def optimize(self, chempiler):
        """Execute the Optimize step and follow the optimization routine"""
