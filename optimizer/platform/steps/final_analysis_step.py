import random
import time
import json
import logging
from typing import List, Callable, Optional, Dict, Any

from xdl import xdl_copy, XDL
from xdl.utils.errors import XDLError
from xdl.steps.base_steps import AbstractStep, AbstractDynamicStep, Step
from chemputerxdl.steps import HeatChill, HeatChillToTemp, Wait, StopHeatChill, Transfer
#from xdl.steps.steps_analysis import RunNMR, RunRaman

from ...utils import SpectraAnalyzer, Algorithm

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
        methods (List): List of analytical methods for material analysis, e.g. Raman, NMR, HPLC, etc.
            Will determine necessary steps to obtain analytical data, e.g. if sampling is required.
    """

