import random
import time
import json
from typing import List, Callable, Optional, Dict, Any

from xdl.utils.errors import XDLError
from xdl.steps.base_steps import AbstractStep, AbstractDynamicStep, Step
from xdl.steps import HeatChill, HeatChillToTemp, Wait, StopHeatChill, Transfer
from xdl.steps.steps_analysis import RunNMR
from typing import Dict

class OptimizeStep(AbstractDynamicStep):
    """Wrapper for a step to run it and detect when the step is complete by NMR.
    Also contains flags to highlight which parameters in the step should be
    optimised. Multiple parameters to optimise can be specified, i.e. time and
    temp both set to True.

    Steps supported:
        temp: Any step with 'temp' property, e.g. HeatChill, HeatChillToTemp
        time: HeatChill, Wait
        volume: Any step with volume property, e.g. Add

    Args:
        id (str): ID to keep track of what parameters are being optimised.
        children (List[Step]): List of steps to optimize parameters for.
            Max length 1. Reason for using a list is for later integration into
            XDL.
        nmr (str): NMR node name.
        on_time_obtained (Callable): Callback function to handle result after
            optimum reaction time is obtained.
        time (bool): If True, will record optimum reaction time using NMR to
            determine if the rxn is complete.
        nmr_delta (float): Absolute difference between two spectra. If the
            absolute difference between two consecutive spectra falls below
            this threshold the reaction is deemed to be complete.
        temp (bool): If True, optimise temp property of child step. Used by
            outer level Optimizer step.
        min_temp (float): Minimum temperature to use in optimisation. Only
            used if temp is True. Used by outer level Optimizer step.
        max_temp (float): Maximum temperature to use in optimisation. Only
            used if temp is True. Used by outer level Optimizer step.
        volume (bool): If True, optimise volume property of child step. Used by
            outer level Optimizer step.
        min_volume (float): Minimum volume to use in optimisation. Only
            used if temp is True. Used by outer level Optimizer step.
        max_volume (float): Maximum volume to use in optimisation. Only
            used if temp is True. Used by outer level Optimizer step.
    """
    def __init__(
        self,
        id: str,
        children: List[Step],
        nmr: str,
        on_time_obtained: Callable,
        time: bool = True,
        nmr_delta: float = 1,
        temp: bool = False,
        min_temp: float = None,
        max_temp: float = None,
        volume: bool = False,
        min_volume: float = None,
        max_volume: float = None,
    ):
        super().__init__(locals())

        # Check there is only one child step.
        if len(children) > 1:
            raise XDLError('Only one step can be wrapped by OptimizeStep.')

        self.step = children[0]

        # Initialise state (only needed if self.time == True)
        self.state = {
            'current_nmr': [],
            'done': False,
        }

    def on_nmr_finish(self, result: List[float]):
        """Check if reaction is done according to the difference in the current
        and last NMR spectrum. Set state['done'] to True if rxn is complete.
        Set state['current_nmr'] to the new NMR spectrum.
        """
        if abs(self.state['current_nmr'] - result) < self.nmr_delta:
            self.state['done'] = True
        self.state['current_nmr'] = result

    def on_start(self):
        # Not optimising time, just execute steps.
        if not self.time:
            return self.children

        # HeatChill step, start heating/chilling and move onto on_continue loop.
        if type(self.step) == HeatChill:
            return [
                HeatChillToTemp(self.step.vessel, self.step.temp, stir=self.step.stir)
            ]

        # Wait step, move straight onto on_continue loop.
        elif type(self.step) == Wait:
            return []

    def on_continue(self):
        # Rxn is complete or not recording time, finish.
        if self.state['done'] or not self.time:
            return []

        # Get start_t and continuously run NMR until rxn is complete.
        self.start_t = time.time()

        return [
            Transfer(from_vessel=self.step.vessel,
                     to_vessel=self.nmr,
                     volume=self.nmr_volume),
            RunNMR(nmr=self.nmr, on_finish=self.on_nmr_finish)
        ]

    def on_finish(self):
        # Not recording time, finish.
        if not self.time:
            return []

        # Send elapsed time to on_time_obtained callback and finish.
        self.end_t = time.time()
        self.on_time_obtained(self.end_t - self.start_t)

        # Stop heating/chilling and finish.
        if type(self.step) == HeatChill:
            return [
                StopHeatChill(vessel=self.step.vessel)
            ]
        
        # No heating/chilling, just finish.
        elif type(self.step) == Wait:
            return []


class Optimizer(AbstractDynamicStep):
    """Outer level wrapper for optimizing multiple parameters in an entire
    procedure.

    <Optimizer>
        <Add  ... />
        <OptimizeStep ... >
            <HeatChill ... />
        </OptimizeStep>
        ...
    </Optimizer>

    Args:
        children (List[Step]): List of steps to execute. Should contain steps
            wrapped by OptimizeStep.
        n_iterations (int): Number of iterations to do before returning optimum
            params found.
        save_path (str): Path to save results to.
    """
    def __init__(
        self,
        children: List[Step],
        n_iterations: int,
        save_path: str
    ):
        self.results = {}
        
        self.state = {
            'iteration': 1
        }

    def get_optimize_steps(self) -> List[OptimizeStep]:
        """Get all OptimizeSteps in self.children."""
        optimize_steps = []
        for step in self.children:
            if type(step) == OptimizeStep:
                optimize_steps.append(step)
        return optimize_steps

    def get_params_template(self) -> Dict[str, Dict[str, Any]]:
        """Get dictionary of all parameters that are to be optimised and
        associated min/max values. Keys are of the form
        f'{optimizestep_id}_{param_to_optimize}' i.e. 'reflux1_temp'
        """
        optimized_steps = self.get_optimize_steps()
        params = {}
        for step in optimized_steps:
            if step.temp:
                params[f'{step.id}_temp'] = {
                    'min': step.min_temp, 'max': step.max_temp, type: 'temp'}
            if step.volume:
                params[f'{step.id}_volume'] = {
                    'min': step.min_volume, 'max': step.max_volume, type: 'temp'}
        return params

    def get_random_params(self) -> Dict[str, float]:
        """Get dictionary of params and random values within specified range for
        all params that are to be optimised. Keys are of the form
        f'{optimizestep_id}_{param_to_optimize}' i.e. 'reflux1_temp'
        """
        template = self.get_params_template()
        params = {}
        for param in template:
            params[param] = random.randint(int(param['min']), int(param['max']))
        return params

    def get_frozenset_params(
        self, params: Optional[Dict[str, float]] = None) -> frozenset:
        """Get frozenset of params for use as a dictionary key.
        
        Args:
            params (Dict[str, float]): Param dictionary to convert to frozenset.
                If None, self.state['params'] will be used.
        
        Returns:
            frozenset: params as frozenset.
        """
        if params == None:
            params = self.state['params']
        return frozenset([(param, val) for param, val in params.items()])

    def on_time_obtained(self, optimizestep_id: str, rxn_time: float) -> None:
        """Callback function for when optimum reaction time is obtained. Stores
        reaction time in self.results and saves self.results.
        
        Args:
            optimizestep_id (str): ID of OptimizeStep which the rxn time relates
                to.
            rxn_time (float): Optimum reaction time found in seconds.
        """
        fs_params = self.get_frozenset_params()
        self.results[fs_params][f'{optimizestep_id}_time'] = rxn_time
        self.save()

    def on_nmr_finished(self, spectrum: List[float]) -> None:
        """Callback function for when NMR spectra has been recorded at end of
        procedure. Stores spectrum in self.results and saves self.results.
        
        Args:
            spectrum (List[float]): Spectrum obtained by NMR.
        """
        fs_params = self.get_frozenset_params()
        self.results[fs_params]['final_nmr'] = spectrum
        self.save()

    def on_start(self) -> None:
        return []

    def on_continue(self) -> None:
        # Reached max number of iterations, finish.
        if self.state['iteration'] >= self.n_iterations:
            return []

        # Get new params and run the procedure, saving all results obtained.
        self.state['params'] = self.get_random_params()
        params = self.state['params']
        fs_params = self.get_frozenset_params(params)
        self.results[fs_params] = {}

        # Adjust OptimizeSteps with new params
        for step in self.children:
            if type(step) == OptimizeStep:
                if step.time:
                    step.on_time_obtained = self.on_time_obtained

                if step.temp:
                    step.step.temp = params[f'{step.id}_temp']

                if step.volume:
                    step.step.volume = params[f'{step.id}_volume']
        
        self.state['iteration'] += 1

        # Run procedure, followed by analysis by NMR and rig cleaning.
        return self.children + [
            Transfer(from_vessel=self.final_vessel, to_vessel=self.nmr, volume=self.nmr_volume),
            RunNMR(nmr=self.nmr, on_finish=self.on_nmr_finish),
        ] + self.cleaning_steps()

    def on_finish(self) -> None:
        return []

    def cleaning_steps(self) -> List[Step]:
        return []

    def save(self) -> None:
        """Save results as JSON to save_path given in __init__."""
        with open(self.save_path, 'w') as fd:
            json.dump({str(fs): res for fs, res in self.results.items()}, fd)
