import time
from typing import List, Callable, Optional, Dict, Any

from xdl.utils.errors import XDLError
from xdl.steps.base_steps import AbstractStep, AbstractDynamicStep, Step
from xdl.steps import HeatChill, HeatChillToTemp, Wait, StopHeatChill, Transfer, StartStir, Stir
#from xdl.steps.steps_analysis import RunNMR

from .utils import SpectraAnalyzer

class Monitor(AbstractDynamicStep):
    """Wrapper for a step to run it and detect when the step is complete by an analysis step.

    Steps supported:
        HeatChill, Wait, Stir
    
    Args:
        children (List): List of steps to monitor parameters for.
            Max length 1. Reason for using a list is for later integration into
            XDL.
        methods (List): List of analytical methods for reaction monitoring, e.g. Raman, NMR, HPLC, etc.
            Will determine necessary steps to obtain analytical data, e.g. if sampling is required.
        time (bool): If True, will use the analysis to determine reaction completion.
        sample_volume (float): Volume of the sample sent for analysis if required. Given internally.
        threshold (float): Relative difference of analytical data (i.e. compound concentration)
            to determine reaction completion.
    """

    def __init__(
        self,
        children: List[Step],
        methods: List,
        time: bool = False,
        sample_volume: float = None,
        threshold: float = 0.05,
    ):
        super().__init__(locals())

        self.analyzer = SpectraAnalyzer(10, 'data_path')

        # Check there is only one child step.
        if len(children) > 1:
            raise XDLError('Only one step can be wrapped by Monitor.')

        self.step = children[0]

        # Initialise state (only needed if self.time == True)
        self.state = {
            'current_state': [],
            'done': False,
        }

    def _get_instrument(self, method):
        """Obtain the instrument for a provided analytical method."""

    def _get_sample_volume(self):
        """Get the sample volume based on the analytical instrument used."""

    def _get_analysis_steps(self, method):
        """Get all steps required to obtained analytical data for a given method."""

    def _on_analysis_finish(self, result: List[float]):
        """Check if reaction is done according to the difference in the current
        and last analysis spectrum. Set state['done'] to True if rxn is complete.
        Set state['current_state'] to the new spectrum.
        """
        if (self.state['current_state'] - result) < self.threshold:
            self.state['done'] = True
        self.state['current_state'] = result

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

        elif type(self.step) == Stir:
            return [
                StartStir(self.step.vessel, self.step.stir_speed)
            ]

    def on_continue(self):
        # Rxn is complete or not recording time, finish.
        if self.state['done'] or not self.time:
            return []

        # Get start_t and continuously run NMR until rxn is complete.
        self.start_t = time.time()

        analysis_steps = [self._get_analysis_steps(method) for method in self.methods]

        return analysis_steps

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
        else:
            return []
