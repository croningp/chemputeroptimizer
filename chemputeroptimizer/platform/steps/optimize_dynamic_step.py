import logging
import os
import json

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

from .steps_analysis import *
from .utils import find_instrument
from ...utils import SpectraAnalyzer, AlgorithmAPI


class OptimizeDynamicStep(AbstractDynamicStep):
    """Outer level wrapper for optimizing multiple parameters in an entire
    procedure.

    Args:
        original_xdl (:obj: XDL): Full XDL procedure to be optimized. Must contain
            some steps wrapped with OptimizeStep steps.
    """

    PROP_TYPES = {
        'original_xdl': XDL,
        'algorithm_class': AlgorithmAPI,
    }

    def __init__(
            self,
            original_xdl: XDL,
            algorithm_class: AlgorithmAPI,
            **kwargs
        ):
        super().__init__(locals())

        self.logger = logging.getLogger('optimizer.dynamic_step')

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

        for i, step in enumerate(self.original_xdl.steps):
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

        self.algorithm_class.load_input(self.parameters, result)

        new_setup = self.algorithm_class.get_next_setup()  # OrderedDict

        for step_id_param, step_id_param_value in new_setup.items():
            self.parameters[step_id_param].update(
                {'current_value': step_id_param_value})

        self.logger.debug('New parameters from algorithm:\n %s',
                          dict(new_setup))

        self._update_xdl()

    def _update_state(self):
        """Updates state attribute when procedure is over"""

        self.state['iteration'] += 1
        self.state['updated'] = True

    def _update_xdl(self):
        """Creates a new copy of xdl procedure with updated parameters and
        saves the .xdl file"""

        # making copy of the raw xdl before any preparations
        # to make future procedure updates possible
        new_xdl = xdl_copy(self.original_xdl)

        for record in self.parameters:
            # slicing the parameter name for step id:
            step_id = int(record[record.index('_') + 1:record.index('-')])
            # slicing for the parameter name
            param = record[record.index('-') + 1:]
            try:
                new_xdl.steps[step_id].children[0].properties[
                    param] = self.parameters[record]['current_value']
            except KeyError:
                raise KeyError(
                    f'Not found the following steps in parameters dictionary: \
{new_xdl.steps[step_id]}.'
                ) from None

        self.logger.debug('Created new xdl object (id %d)',
                          id(self.working_xdl_copy))

        self.working_xdl_copy = new_xdl

        self.save()

        self.working_xdl_copy.prepare_for_execution(self._graph,
                                                    interactive=False)
        self._update_analysis_steps()

    def on_prepare_for_execution(self, graph):
        """Additional preparations before execution"""

        self.logger.debug('Preparing Optimize dynamic step for execution.')

        # saving graph for future xdl updates
        self._graph = graph
        # getting parameters from the *raw* xdl
        self._get_params_template()
        # initializing algorithm
        self.algorithm_class.initialize(self.parameters)
        # working with _protected copy to avoid step reinstantiating
        self.working_xdl_copy = xdl_copy(self.original_xdl)
        self.working_xdl_copy.prepare_for_execution(graph, interactive=False)
        self._update_analysis_steps()

        # load necessary tools
        self._analyzer = SpectraAnalyzer()

        self.state = {
            'iteration': 1,
            'current_result': {key: -1 for key in self.target},
            'updated': True,
            'done': False,
        }

    def load_optimization_config(self, **kwargs):
        """Update the optimization configuration if required"""
        for k, v in kwargs.items():
            self.__dict__[k] = v

    def _update_analysis_steps(self):
        """Updates the analysis steps"""

        analysis_method = None

        for step in self.working_xdl_copy.steps:
            if step.name == 'FinalAnalysis':
                analysis_method = step.method
                if analysis_method == 'interactive':
                    step.on_finish = self.interactive_final_analysis_callback
                    continue
                step.on_finish = self.on_final_analysis

        if analysis_method is None:
            self.logger.info('No analysis steps found!')
            return

        if analysis_method == 'interactive':
            self.logger.info('Running with interactive FinalAnalysis method')
            return

        self._get_blank_spectrum(self._graph, analysis_method)

    def _get_blank_spectrum(self, graph, method):
        """Step to measure blank spectrum"""

        instrument = find_instrument(graph, method)

        if method == 'Raman':
            self.working_xdl_copy.steps.insert(
                0,
                RunRaman(
                    raman=instrument,
                    on_finish=lambda spec: None,
                    blank=True
                )
            )
            self.logger.debug('Added extra RunRaman blank step.')

    def interactive_final_analysis_callback(self):
        """Callback function to promt user input for final analysis"""

        msg = 'You are running FinalAnalysis step interactively.\n'
        msg += f'Current procedure is running towards >{self.target}< parameters.\n'
        msg += 'Please type the result of the analysis below\n'
        msg += '***as <target_parameter>: <current_value>***\n'

        while True:
            answer = input(msg)
            # TODO check with regex
            param, param_value = answer.split(':')

            try:
                self.logger.info('Last value for %s is %.02f, updating.',
                                 param, self.state['current_result'][param])
                self.state['current_result'][param] = float(param_value)
            except KeyError:
                key_error_msg = f'{param} is not valid target parameter\n'
                key_error_msg += 'try one of the following:\n'
                key_error_msg += '>>>' + '  '.join(self.target.keys()) + '\n'
                self.logger.warning(key_error_msg)
            except ValueError:
                self.logger.warning('Value must be float!')
            else:
                break

        self.state['updated'] = False

    def on_final_analysis(self, data):
        """Callback function for when spectra has been recorded at end of
        procedure. Updates the state (current result) parameter.

        Args:
            data (Any): Spectral data (e.g. NMR) of the final product
        """

        self._analyzer.load_spectrum(data)

        # final parsing occurs in SpectraAnalyzer.final_analysis
        result = self._analyzer.final_analysis()

        self.state['current_result'] = result

        # setting the updated tag to false, to update the
        # procedure when finished
        self.state['updated'] = False

    def _check_termination(self):

        if self.state['iteration'] > self.max_iterations:
            self.logger.info('Max iterations reached. Done.')
            return True

        if self.state['current_result']['final_parameter'] >= self.target[
                'final_parameter']:
            self.logger.info('Target parameter reached. Done.')
            return True

        else:
            return False

    def on_start(self):

        return []

    def on_continue(self):

        self.logger.info(
            'Optimize Dynamic step running, current iteration: <%d>; current result: <%s>',
            self.state['iteration'], self.state['current_result'])

        if self._check_termination():
            return []

        if not self.state['updated']:
            self.update_steps_parameters(self.state['current_result'])
            self._update_state()

        return self.working_xdl_copy.steps

    def on_finish(self):
        return []

    def cleaning_steps(self):
        pass

    def save(self):
        """Saves the data for the current iteration"""

        current_path = os.path.join(
            os.path.dirname(self.original_xdl._xdl_file),
            'iterations',
            str(self.state['iteration'])
        )
        os.makedirs(current_path, exist_ok=True)

        original_filename = os.path.basename(self.original_xdl._xdl_file)

        # saving xdl
        self.working_xdl_copy.save(
            os.path.join(
                current_path,
                original_filename[:-4] + '_' + str(self.state['iteration']) +
                '.xdl',
            ))

        # saving parameters
        params_file = os.path.join(
            current_path,
            original_filename[:-4] + '_params.json',
        )
        with open(params_file, 'w') as f:
            json.dump(self.parameters, f)

        # saving algorithmic data
        alg_file = os.path.join(
            current_path,
            original_filename[:-4] + '_data.csv',
        )
        self.algorithm_class.save(alg_file)
