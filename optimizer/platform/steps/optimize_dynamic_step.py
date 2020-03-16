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
        target (Dict): Dictonary of target parameter, e.g. {'final_yield': 0.75}.
        save_path (str): Path to save results to.
        optimize_steps (List[Step], optional): List of optimization steps.
        reference (Any, optional): Optional reference for the target product,
            may be supplied as :float: reference peak or :array: reference spectrum.
    """

    PROP_TYPES = {
        'xdl_object': XDL,
        'max_iterations': int,
        'target': Dict,
        'save_path': str,
        'optimize_steps': List,
        'reference': Any,
        'algorithm': str,
    }

    def __init__(
            self,
            xdl_object: XDL,
            max_iterations: int,
            target: Dict,
            save_path: str,
            algorithm: str,
            optimize_steps: List[Step] = None,
            reference: Any = None,
            **kwargs
        ):
        super().__init__(locals())

        self.logger = logging.getLogger('dynamic optimize step')

        if not hasattr(self, '_analyzer'): self._analyzer = SpectraAnalyzer()
        if not hasattr(self, '_algorithm'): self._algorithm = Algorithm(algorithm)
        if not hasattr(self, 'parameters'): self._get_params_template()
        if not hasattr(self, 'state'): self.state = {
            'iterations': 0,
            'current_result': 0,
        }

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

        if self.optimize_steps:
            for optimize_step, optimize_step_instance in self.optimize_steps.items():
                param_template.update({
                    f'{optimize_step}-{param}': {
                        **optimize_step_instance.optimize_properties[param],
                        'current_value': optimize_step_instance.children[0].properties[param]
                    }
                    for param in optimize_step_instance.optimize_properties
                })

        for i, step in enumerate(self.xdl_object.steps):
            if step.name == 'OptimizeStep':
                param_template.update(
                    {
                        f'{step.children[0].name}_{i}-{param}': {
                            **step.optimize_properties[param],
                            'current_value': step.children[0].properties[param]
                        }
                        for param in step.optimize_properties
                    }
                )
        self.parameters = param_template

    def update_steps_parameters(self, result: Dict) -> None:
        """Updates the parameter template and corresponding procedure steps"""

        self._algorithm.load_input(self.parameters, result)

        new_setup = self._algorithm.optimize() # OrderedDict
        
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
                if self.optimize_steps:
                    new_xdl.steps[step_id].properties[param] = self.parameters[record]['current_value']
                    self.optimize_steps[record[:record.index('-')]].children[0].properties[param] = self.parameters[record]['current_value']
                else:
                    new_xdl.steps[step_id].children[0].properties[param] = self.parameters[record]['current_value']
            except KeyError:
                print('KeyError')

        new_xdl.save('new_xdl.xdl')

        self.xdl_object = new_xdl
        self.on_prepare_for_execution(self._graph)

    def on_prepare_for_execution(self, graph):
        
        self._graph = graph
        self.xdl_object.prepare_for_execution(graph, interactive=False)
        self._update_final_analysis_steps()

    def _update_final_analysis_steps(self):
        """Updates the final analysis method according to target parameter"""

        for step in self.xdl_object.steps:
            if step.name == 'FinalAnalysis':
                step.on_finish = self.on_final_analysis

    def on_final_analysis(self, data):
        """Callback function for when spectra has been recorded at end of
        procedure. Updates the target parameter.

        Args:
            data (Any): Spectral data (e.g. NMR) of the final product
        """

        self._analyzer.load_spectrum(data)

        # if looking for specific parameters in a final spectrum:
        if 'spectrum' in self.target:
            result = self._analyzer.final_analysis(
                reference=self.reference,
                target=self.target['spectrum'],
            )

            self.state['current_result'] = result

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
