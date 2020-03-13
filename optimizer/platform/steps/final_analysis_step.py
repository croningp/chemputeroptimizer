from typing import List, Callable, Optional, Dict, Any

from networkx import MultiDiGraph

from xdl import xdl_copy, XDL
from xdl.utils.errors import XDLError
from xdl.steps.base_steps import AbstractStep, Step
from chemputerxdl.steps import (
    HeatChill,
    HeatChillToTemp,
    Wait,
    StopHeatChill,
    Transfer,
    Dissolve,
    Stir,
)

from .steps_analysis import RunRaman
from ...utils import SpectraAnalyzer
from ...utils.errors import OptimizerError
from ...constants import (
    SUPPORTED_ANALYTICAL_METHODS,
    SUPPORTED_FINAL_ANALYSIS_STEPS,
    ANALYTICAL_INSTRUMENTS,
)

def find_instrument(graph: MultiDiGraph, method: str) -> str:
    """Get the analytical instrument for the given method
    
    Args:
        method (str): Name of the desired analytical method
        
    Returns:
        str: ID of the analytical instrument on the supplied graph
    """
    for node, data in graph.nodes(data=True):
        if data['class'] == ANALYTICAL_INSTRUMENTS[method]:
            return node

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
        'sample_volume': int,
        'instrument': str,
        'on_finish': Any,
    }

    INTERNAL_PROPS = [
        'instrument',
    ]

    def __init__(
            self,
            children: List[Step],
            method: str,
            sample_volume: Optional[int] = None,
            on_finish: Optional[Any] = None,

            # Internal properties
            instrument: Optional[str] = None,
            **kwargs
        ) -> None:
        super().__init__(locals())

        # check if method is valid
        if method not in SUPPORTED_ANALYTICAL_METHODS:
            raise OptimizerError(f'Specified method {method} is not supported')

        # Check there is only one child step.
        if len(children) > 1:
            raise XDLError('Only one step can be wrapped by OptimizeStep.')
        self.step = children[0]

        # check if the supported step was wrapped
        if self.children[0].name not in SUPPORTED_FINAL_ANALYSIS_STEPS:
            raise OptimizerError(f'Substep {self.step.name} is not supported to run final analysis')

    def on_prepare_for_execution(self, graph: MultiDiGraph) -> None:
        
        self.instrument = find_instrument(graph, self.method)

    def get_steps(self) -> List[Step]:
        steps = []
        steps.extend(self.children)

        # reaction is complete and reaction product 
        # remains in reaction vessel
        if isinstance(self.children[0], (HeatChill, HeatChillToTemp, Wait, Stir)):
            try:
                if not 18 <= self.children[0].temp <= 30: # checking for steps temperature
                    raise OptimizerError('Final analysis only supported for room temperature \
                        reaction mixture!')
            except AttributeError:
                pass
            
            steps.extend(self._get_analytical_steps())

        # TODO support other steps wrapped wiht FinalAnalysis, i.e. Filter, Dry
        # required additional preparation of the sample, e.g. dissolution

        return steps

    def _get_analytical_steps(self) -> List:
        """Obtaining steps to perform analysis based on internal method attribute"""
        
        # Raman
        # no special prepartion needed, just measure the spectrum
        if self.method == 'Raman':
            return [
                RunRaman(
                    raman=self.instrument,
                    on_finish=self.on_finish,
                )
            ]

        # TODO add implied steps for additional analytical methods
        # HPLC, NMR, pH
        
        return []
