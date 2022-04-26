import time
from typing import List, Callable, Optional, Dict, Any

from networkx import MultiDiGraph

from xdl.errors import XDLError
from xdl.steps.base_steps import AbstractStep, AbstractDynamicStep, Step
from xdl.steps.special_steps import Async, Await
from chemputerxdl.steps import HeatChill, HeatChillToTemp, Wait, StopHeatChill, Transfer, StartStir, Stir
from .steps_analysis.utils import find_instrument
from .steps_analytical_instruments import RunRaman

# from .utils import SpectraAnalyzer


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
        method: str = "Raman",
        sampling_delay = 2.0,
        time: bool = False,
        sample_volume: float = None,
        threshold: float = 0.05,
    ):
        super().__init__(locals())

        #self.analyzer = SpectraAnalyzer(10, 'data_path')

        # Check there is only one child step.
        if len(children) > 1:
            raise XDLError('Only one step can be wrapped by Monitor.')

        self.step = children[0]

        # Initialise state (only needed if self.time == True)
        self.state = {
            'current_state': [],
            'done': False,
        }

        self.method = method
        self.sampling_delay = sampling_delay

    def on_prepare_for_execution(self, graph: MultiDiGraph) -> None:

        self.instrument = find_instrument(graph, self.method)


    def _get_analysis_steps(self, method):
        """Get all steps required to obtained analytical data for a given method."""

        # Raman
        # no special prepartion needed, just measure the spectrum
        if self.method == 'Raman':
            return [
                RunRaman(
                    raman=self.instrument,
                    on_finish=self._on_analysis_finish,
                )
            ]
        else:
            raise NotImplementedError(f"{method} is not a supported method.")

    def _on_analysis_finish(self, result: List[float]):
        """Check if reaction is done according to the difference in the current
        and last analysis spectrum. Set state['done'] to True if rxn is complete.
        Set state['current_state'] to the new spectrum.
        """
        pass

    def _on_child_finish(self):
        """Check if reaction is done according to the difference in the current
        and last analysis spectrum. Set state['done'] to True if rxn is complete.
        Set state['current_state'] to the new spectrum.
        """
        self.state['done'] = True

    def on_start(self):
        # Not optimising time, just execute steps.

        return [Async(
            pid="monitoring",
            children=[self.step],
            on_finish=self._on_child_finish)]

    def on_continue(self):
        # Rxn is complete or not recording time, finish.
        if self.state['done']:
            return []

        # Get start_t and continuously run NMR until rxn is complete.
        self.start_t = time.time()

        time.sleep(self.sampling_delay)

        return self._get_analysis_steps(self.method)

    def on_finish(self):
        return []
