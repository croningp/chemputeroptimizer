import random
import time
import json
import logging
from typing import List, Callable, Optional, Dict, Any

from xdl import xdl_copy, XDL
from xdl.utils.errors import XDLError
from xdl.steps.base_steps import AbstractStep, AbstractDynamicStep, Step
from chemputerxdl.steps import (
    HeatChill,
    HeatChillToTemp,
    Wait,
    StopHeatChill,
    Transfer,
    Dissolve,
    Add,
    Stir,
)
#from xdl.steps.steps_analysis import RunNMR, RunRaman

from ...utils import SpectraAnalyzer, Algorithm
from ...utils.errors import OptimizerError
from ...constants import (
    SUPPORTED_ANALYTICAL_METHODS,
    SUPPORTED_FINAL_ANALYSIS_STEPS,
)

class FinalAnalysis(AbstractStep):
    """Wrapper for a step to obtain final yield and purity. Should be used
    to indicate the last step of the procedure where pure material is obtained.

    Steps supported:
        Dry: material was dried and needs to be dissolved for analysis
        Evaporate: material was concentrated and needs to be dissolved for analysis
        Filter (solid): solid material was filtered and needs to be dissolved for analysis
        Filter (filtrate) : dissolved material was filtered and filtrate could be analyzed directly

    Args:
        children (List[Step]): List of steps to obtain final analysis from.
            Max length 1. Reason for using a list is for later integration into
            XDL.
        method (str): Name of the analytical method for material analysis, e.g. Raman, NMR, HPLC, etc.
            Will determine necessary steps to obtain analytical data, e.g. if sampling is required.
    """
    PROP_TYPES = {
        'children': List,
        'method': List,
    }

    def __init__(
            self,
            children: List[Step],
            method: str,
            **kwargs
        ):
        super().__init__(locals())

        # check if method is valid
        if method not in SUPPORTED_ANALYTICAL_METHODS:
            raise OptimizerError(f'Specified method {method} is not supported')

        # Check there is only one child step.
        if len(children) > 1:
            raise XDLError('Only one step can be wrapped by OptimizeStep.')
        self.step = children[0]

        # check if the supported step was wrapped
        if self.step.name not in SUPPORTED_FINAL_ANALYSIS_STEPS:
            raise OptimizerError(f'Substep {self.step.name} is not supported to run final analysis')

    def get_steps(self):
        # handling all methods separately
        if self.method == 'Raman':
            pass
            # # TODO check for connection between vessel and Analytical instrument
            
            # # reaction is over 
            # if self.step in [HeatChill, Wait, Stir]:
            #     return self.children # + RunRaman
