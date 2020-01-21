"""
Module to run chemical reaction optimization.
"""

from xdl import XDL

from .steps import Optimize

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

        self._xdl_object = XDL(procedure)

    def prepare_for_optimization(self, interactive):
        """Get the Optimize step and the respective parameters"""
        #self._xdl_object.prepare_for_execution(self.graph, interactive)
        #self.optimizer = Optimize(self._xdl_object)
        #self._validate_otpimization_parameters(interactive)

    def _validate_otpimization_parameters(self, interactive):
        """Get the optimization parameters and validate them if needed"""

    def optimize(self, chempiler):
        """Execute the Optimize step and follow the optimization routine"""
        
        #self.optimizer.execute(chempiler)
