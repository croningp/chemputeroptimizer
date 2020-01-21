"""
Module to run chemical reaction optimization.
"""

import logging

from xdl import XDL

from .steps import Optimize
from .platform import OptimizerPlatform
from .constants import (SUPPORTED_STEPS, SUPPORTED_PARAMETERS)
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

        self._optimization_steps = []

        self.logger = logging.getLogger('optimizer')

    def prepare_for_optimization(self, interactive=False):
        """Get the Optimize step and the respective parameters"""

        # get the steps for optimization
        self._get_optimization_steps(interactive)

        # check the steps for optimization and their parameters
        self._check_otpimization_steps_and_parameters()

        # create an Optimize step
        #self._xdl_object.prepare_for_execution(self.graph, interactive)
        #self.optimizer = Optimize(self._xdl_object)
        #self._validate_otpimization_parameters(interactive)

    def _check_otpimization_steps_and_parameters(self):
        """Get the optimization parameters and validate them if needed"""

        for opt_step in self._optimization_steps:
            if opt_step.step.name not in SUPPORTED_STEPS:
                raise OptimizerError(
                    "The following step is not supported for optimization: <{}>".format(opt_step.step.name))
            if opt_step.id not in SUPPORTED_PARAMETERS[opt_step.step.name]:
                raise ParameterError(
                    "The following parameters <{}> are not valid for the selected step: <{}>".format(opt_step.id, opt_step.step.name)
            )

    def _get_optimization_steps(self, interactive=False):
        """Get the optimization steps from the given procedure"""

        # allow user to choose steps and their parameters for optimization
        if interactive:
            pass
        
        # iterate through xdl procedure and peak all OptimizeStep steps
        for step in self._xdl_object.steps:
            if step.name == "OptimizeStep":
                self._optimization_steps.append(step)

    def optimize(self, chempiler):
        """Execute the Optimize step and follow the optimization routine"""
        
        #self.optimizer.execute(chempiler)
