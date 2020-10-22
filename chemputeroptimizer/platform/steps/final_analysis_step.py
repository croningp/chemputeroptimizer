from typing import List, Callable, Optional, Dict, Any

from networkx import MultiDiGraph

from xdl.errors import XDLError
from xdl.constants import JSON_PROP_TYPE
from xdl.steps.base_steps import AbstractStep, Step
from xdl.steps.special_steps import Callback
from chemputerxdl.steps import (
    HeatChill,
    HeatChillToTemp,
    Wait,
    StopHeatChill,
    Transfer,
    Dissolve,
    Stir,
    Add,
)

from .analysis_step import Analyze
from .steps_analysis import RunRaman, RunNMR
from .utils import find_instrument, find_nearest_waste
from ...utils import SpectraAnalyzer
from ...utils.errors import OptimizerError
from ...constants import (
    SUPPORTED_ANALYTICAL_METHODS,
    SUPPORTED_FINAL_ANALYSIS_STEPS,
)


class FinalAnalysis(Analyze):
    """Support for a step to obtain final yield and purity. Should be used
    after the last step of the procedure where pure material is obtained.

    Steps supported:
        Stir: reaction is over and product remains in a reaction vessel.
        HeatChill/HeatChillToTemp: reaction is over and product remains in a
            reaction vessel (only at or near room temperature).

    Args:
        vessel (str): Name of the vessel (on the graph) where final product
            remains at the end of the reaction.
        method (str): Names of the analytical method for material
            analysis, e.g. Raman, NMR, HPLC, etc. Will determine necessary steps
            to obtain analytical data, e.g. if sampling is required.
        sample_volume (int): Volume of product sample to be sent to the
            analytical instrument. Either supplied, or determined in the graph.
    """

    PROP_TYPES = {
        'vessel': str,
        'method': str,
        'sample_volume': float,
        'instrument': str,
        'on_finish': Callable,
        'reference_step': JSON_PROP_TYPE,
        'method_props': JSON_PROP_TYPE,
        'injection_pump': str,
        'sample_transfer_volume': float,
        'cleaning_solvent': str,
        'cleaning_solvent_vessel': str,
        'nearest_waste': str,
    }

    INTERNAL_PROPS = [
        'instrument',
        'reference_step',
        'cleaning_solvent',
        'nearest_waste',
        'injection_pump',
        'sample_transfer_volume',
        'cleaning_solvent_vessel',
    ]

    DEFAULT_PROPS = {
        'on_finish': lambda spec: None,
        # volume left in the syringe after sample is injected
        'sample_transfer_volume': 2,
        'method_props': {},
    }

    def __init__(
            self,
            vessel: str,
            method: str,
            sample_volume: Optional[float] = None,
            on_finish: Optional[Callable] = 'default',
            method_props: JSON_PROP_TYPE = 'default',

            # Internal properties
            instrument: Optional[str] = None,
            reference_step: Optional[JSON_PROP_TYPE] = None,
            cleaning_solvent: Optional[str] = None,
            nearest_waste: Optional[str] = None,
            injection_pump: Optional[str] = None,
            sample_transfer_volume: Optional[float] = 'default',
            cleaning_solvent_vessel: Optional[str] = None,
            **kwargs
        ) -> None:

        print('#### LOCALS ####\n', locals())
        Analyze.__init__(**locals())

        # check if method is valid
        if method not in SUPPORTED_ANALYTICAL_METHODS:
            raise OptimizerError(f'Specified method {method} is not supported')
