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
)

from ...utils import SpectraAnalyzer, Algorithm

class Optimize(AbstractDynamicStep):
    """Outer level wrapper for optimizing multiple parameters in an entire
    procedure.

    e.g.
    <Optimize>
        <Add  ... />
        <OptimizeStep ... >
            <HeatChill ... />
        </OptimizeStep>
        <Filter />
        ...
    </Optimize>

    Args:
        children (List[Step]): List of steps to execute. Optionally contain some
            steps wrapped by OptimizeStep.
        max_iterations (int): Maximum number of iterations.
        criteria (float): Target value.
        save_path (str): Path to save results to.
        optimize_steps (List[Step], optional): List of optimization steps.
        reference (Any, optional): Optional reference for the target product,
            may be supplied as :float: reference peak or :array: reference spectrum.
    """

    PROP_TYPES = {
        'xdl_object': XDL,
        'max_iterations': int,
        'criteria': float,
        'save_path': str,
        'optimize_steps': List,
        'reference': Any,
    }

    def __init__(
            self,
            xdl_object: XDL,
            max_iterations: int,
            criteria: float,
            save_path: str,
            optimize_steps: List[Step] = None,
            reference: Any = None,
            **kwargs
        ):
        super().__init__(locals())

        #self.steps = xdl_object.steps

        self.target = None
        self.parameters = None

        self.tick = 0

        self.logger = logging.getLogger('dynamic optimize step')

        self.algorithm = Algorithm()

        self._get_params_template()

    def _get_params_template(self) -> None:
        """Get dictionary of all parametrs to be optimized.
        
        Updates parameters attribute in form:
            (Dict): Nested dictionary of optimizing steps and corresponding parameters of the form:
                {
                    "step_ID-parameter": {
                        "max_value": <maximum parameter value>,
                        "min_value": <minimum parameter value>,
                        "current_value": <parameter value>,
                    }
                }

        Example:
            {
                "HeatChill_1-temp": {
                    "max_value": 70,
                    "min_value": 25,
                    "current_value": 35,
                }
            }
        """
        param_template = {}

        for optimize_step, optimize_step_instance in self.optimize_steps.items():
            param_template.update({
                f'{optimize_step}-{param}': {
                    **optimize_step_instance.optimize_properties[param],
                    'current_value': optimize_step_instance.children[0].properties[param]
                }
                for param in optimize_step_instance.optimize_properties
            })

        self.parameters = param_template

    def update_steps_parameters(self, result: Dict) -> None:
        """Updates the parameter template and corresponding procedure steps"""

        self.algorithm.load_input(self.parameters, result)

        new_setup = self.algorithm.optimize() # OrderedDict
        
        for step_id_param, step_id_param_value in new_setup.items():

            self.parameters[step_id_param].update({'current_value': step_id_param_value})

        print('New parameters: ', self.parameters)

        self._update_xdl()

    def _update_xdl(self):
        """Creates a new copy of xdl procedure with updated parameters and saves the .xdl file"""

        new_xdl = xdl_copy(self.xdl_object)

        for record in self.parameters:
            # slicing the parameter name for step id:
            step_id = int(record[record.index('_')+1:record.index('-')])
            # slicing for the parameter name
            param = record[record.index('-')+1:]
            try:
                new_xdl.steps[step_id].properties[param] = self.parameters[record]['current_value']
            except KeyError:
                print('KeyError')

        new_xdl.save('new_xdl.xdl')

        self.xdl_object = new_xdl

    def get_final_analysis_steps(self, method):
        """Get all steps required to obtained analytical data for a given method

        Args:
            method (str): A given method for an analytical technique, e.g. Raman, NMR, HPLC

        Returns:
            (List): List of XDL steps required to obtain analytical data, i.e. sampling and analysis
        """

    def on_final_analysis(self, data, reference):
        """Callback function for when spectra has been recorded at end of
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