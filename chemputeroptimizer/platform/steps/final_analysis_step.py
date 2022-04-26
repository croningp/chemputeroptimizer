"""Deprecated high-level XDL step to perform reactionanalysis."""

from typing import Callable, Optional

from xdl.constants import JSON_PROP_TYPE

from .analysis_step import Analyze


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
        # step related
        'vessel': str,
        'method': str,
        'sample_volume': float,
        'instrument': str,
        'on_finish': Callable,
        'reference_step': JSON_PROP_TYPE,
        'method_props': JSON_PROP_TYPE,
        'batch_id': str,
        # method related
        'cleaning_solvent': str,
        'cleaning_solvent_vessel': str,
        'priming_waste': str,
        # sample related
        'sample_pump': str,
        'injection_pump': str,
        'sample_excess_volume': float,
        'dilution_vessel': str,
        'dilution_volume': float,
        'dilution_solvent': str,
        'dilution_solvent_vessel': str,
        'distribution_valve': str,
        'injection_waste': str,
        'force_shimming': bool,
        'shimming_solvent_flask': str,
        'shimming_reference_peak': float, # for correct shimming
    }

    INTERNAL_PROPS = [
        'instrument',
        'reference_step',
        'priming_waste',
        'sample_pump',
        'injection_pump',
        'sample_excess_volume',
        'cleaning_solvent_vessel',
        'dilution_vessel',
        'dilution_solvent_vessel',
        'distribution_valve',
        'injection_waste',
        'shimming_solvent_flask',
        'shimming_reference_peak',
        'batch_id',
    ]

    DEFAULT_PROPS = {
        # anonymous function to take 1 argument and return None
        'on_finish': lambda spec: None,
        # volume left in the syringe after sample is injected
        'sample_excess_volume': 2,
        'method_props': {},
        'force_shimming': False,
    }

    def __init__(
            self,
            vessel: str,
            method: str,
            cleaning_solvent: Optional[str] = None,
            sample_volume: Optional[float] = None,
            on_finish: Optional[Callable] = 'default',
            method_props: JSON_PROP_TYPE = 'default',
            dilution_volume: Optional[float] = None,
            dilution_solvent: Optional[str] = None,
            force_shimming: Optional[bool] = 'default',

            # Internal properties
            instrument: Optional[str] = None,
            reference_step: Optional[JSON_PROP_TYPE] = None,
            priming_waste: Optional[str] = None,
            sample_pump: Optional[str] = None,
            injection_pump: Optional[str] = None,
            sample_excess_volume: Optional[float] = 'default',
            cleaning_solvent_vessel: Optional[str] = None,
            dilution_solvent_vessel: Optional[str] = None,
            dilution_vessel: Optional[str] = None,
            injection_waste: Optional[str] = None,
            distribution_valve: Optional[str] = None,
            shimming_solvent_flask: Optional[str] = None,
            shimming_reference_peak: Optional[float] = None,
            batch_id: Optional[str] = None,

            **kwargs
        ) -> None:

        Analyze.__init__(**locals())
