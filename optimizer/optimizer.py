import random
import time
import json
from typing import List, Callable, Optional, Dict, Any

from xdl.utils.errors import XDLError
from xdl.steps.base_steps import AbstractStep, AbstractDynamicStep, Step
from xdl.steps import HeatChill, HeatChillToTemp, Wait, StopHeatChill, Transfer
from xdl.steps.steps_analysis import RunNMR, RunRaman
from typing import Dict

from .utils import SpectraAnalyzer, Algorithm

class OptimizeStep(AbstractStep):
    """Wrapper for a step to be optimised

    Steps and parameters supported:
        Add: addition volume
        HeatChill, HeatChillToTemp: reaction temperature
        HeatChill, Wait, Stir: reaction time

    Args:
        id (str): ID to keep track of what parameters are being optimised.
        children (List[Step]): List of steps to optimize parameters for.
            Max length 1. Reason for using a list is for later integration into
            XDL.
        max_value (float): Minimum parameter value for the optimization routine.
        min_value (float): Maximum parameter value for the optimization routine.
    
    Example:
        ...
        <OptimizeStep "max_value"=1.2, "min_value"=3.2
            <Add
                "reagent"="reagent"
                "volume"=volume
            <Add />
        <OptimizeStep />
        <OptimizeStep "max_value"=70, "min_value"=25
            <HeatChill "temp"=temperature />
        <OptimizeStep />
        ...
    """

    def __init__(
        self,
        id: str,
        children: List[Step],
        max_value: float = None,
        min_value: float = None,
    ):
        super().__init__(locals())
        
        # Check there is only one child step.
        if len(children) > 1:
            raise XDLError('Only one step can be wrapped by OptimizeStep.')

        self.step = children[0]

        self.analyzer = SpectraAnalyzer(5, 'data_path')
        self.algorithm = Algorithm('<algorithm_name', 30)

    def _get_optimized_parameters(self):
        pass

    def _check_input(self):
        pass

    def get_steps(self):
        return self.children

    def human_readable(self, language='en'):
        pass

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

class Optimizer(AbstractDynamicStep):
    """Outer level wrapper for optimizing multiple parameters in an entire
    procedure.

    e.g.
    <Optimizer>
        <Add  ... />
        <OptimizeStep ... >
            <HeatChill ... />
        </OptimizeStep>
        <Filter />
        ...
    </Optimizer>

    Args:
        children (List[Step]): List of steps to execute. Should contain some
            steps wrapped by OptimizeStep.
        max_iterations (int): Maximum number of iterations.
        criteria (float): Target value.
        save_path (str): Path to save results to.
    """

    def __init__(self):
        pass

    def get_optimize_steps(self):
        """Get all OptimizeSteps in children steps"""

    def get_params_template(self) -> Dict[str, float]:
        """Get dictionary of all parametrs to be optimized.
        
        Returns:
            (Dict): Nested dictionary of optimizing steps and corresponding parameters of the form:
                {
                    "parameterID": {
                        "value": <parameter value>,
                        "max": <maximum parameter value>,
                        "min": <minimum parameter value>,
                    }
                }

        Example:
            {
                "HeatChill1_temp": {
                    "value": 35,
                    "max": 70,
                    "min": 25,
                }
            }
        """

    def get_new_params(self, result: Dict) -> Dict:
        """Calls the algorithm optimizer to yield and update a parameter set.
        
        Args:
            result (Dict): Dictionary with input parameters and final result, e.g.:
                {
                    "<stepID>_<parameter>": "<parameter value>",
                    ...
                    "<target_parameter>": "<current value>",
                }

        Returns:
            (Dict): Dictionary with new set of input parameters
        """

    def get_final_analysis_steps(self, method):
        """Get all steps required to obtained analytical data for a given method

        Args:
            method (str): A given method for an analytical technique, e.g. Raman, NMR, HPLC

        Returns:
            (List): List of XDL steps required to obtain analytical data, i.e. sampling and analysis
        """

    def on_final_analysis(self, data, reference):
        """Callback function for when NMR spectra has been recorded at end of
        procedure. Updates the target parameter.

        Args:
            data (Any): Spectral data (e.g. NMR) of the final product
            reference (Any): A reference spectral data (e.g. peak_ID or full spectra) to
                obtain quantitative yield and purity
        """

    def on_start(self):
        pass

    def on_continue(self):
        pass

    def on_finish(self):
        pass

    def cleaning_steps(self):
        pass

    def save(self):
        pass
