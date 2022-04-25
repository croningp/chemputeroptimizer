"""
Generic interface class for all steps dedicated for analysis.
"""

# pylint: disable=unused-argument,attribute-defined-outside-init

import typing
from typing import Callable, Union, Optional
from abc import abstractmethod

from xdl.constants import JSON_PROP_TYPE
from xdl.steps.base_steps import AbstractStep

from chemputerxdl.steps.base_step import ChemputerStep
from chemputerxdl.utils.execution import (
    get_nearest_node,
    get_reagent_vessel,
    get_pump_max_volume
)
from chemputerxdl.constants import (
    CHEMPUTER_PUMP,
    CHEMPUTER_WASTE,
)

from ..utils import (
    find_instrument,
    get_dilution_flask,
)
from .utils import (
    validate_cleaning,
    validate_dilution
)

if typing.TYPE_CHECKING:
    from AnalyticalLabware.devices.chemputer_devices import AbstractSpectrum
    from networkx import MultiDiGraph

class AbstactAnalyzeStep(ChemputerStep, AbstractStep):
    """Abstract step to run the analysis.

    Args:
        vessel (str): Name of the vessel containing the analyte.
        sample_volume (float): Volume of the product sample to be sent to the
            analytical instrument. If not given - no sample is taken and the
            analysis performed as is (i.e., assuming contactless or immersion
            probe).
        dilution_volume (float): Volume of the solvent used to dilute the
            sample before analysis. If not given - no dilution is performed.
        dilution_solvent (str): Solvent used to dilute the sample if
            dilution_volume is given.
        cleaning_solvent (str): Solvent used to clean the analytical instrument
            (if analyte was sampled) and/or dilution vessel (if dilution was
            performed).
        method (str): Method used for the analysis. Defines the instrument to
            be used.
        method_properties (dict): Dictionary with additional properties, passed
            to the low-level analysis step.
        on_finish (Callable[[str], Callable]): Callback function to execute
            when analysis is performed. This function should accept a string
            argument and return a new callable -> the one which is passed to
            the low-level analytical step and executed with a spectrum as an
            argument.
        on_finish_arg (str): Argument for the on_finish callback factory.
        reference_step (dict): Properties from the "reference" step, that
            dictates the necessary preparations before the analysis. E.g.,
            cooling reaction mixture from previous HeatChill step.
    Attrs aka INTERNAL_PROPS:
        instrument (str): Name of the analytical instrument on graph.
        cleaning_solvent_vessel (str): Name of the cleaning solvent vessel on
            the graph.
        priming_waste (str): Name of the waste container to dispose the sample
            after tubing priming.
        sample_pump (str): Name of the pump to withdraw the sample, i.e. pump
            closest to the "vessel".
        injection_pump (str): Name of the pump to inject the sample, i.e. pump
            closest to the "instrument".
        sample_excess_volume (float): Extra volume taken with sample to
            eliminate air gap during sample injection. Is either discarded to
            "injection_waste" or returned to the sample "vessel".
        injection_waste (str): Name of the waste container to discard the
            excess/remaining of the sample after injection.
        dilution_vessel (str): Name of the container to dilute the sample.
            Should have a stirrer, otherwise sample dilution is not guaranteed.
        dilution_solvent_vessel (str): Name of the dilution solvent vessel on
            the graph.
    """

    PROP_TYPES = {
        # step related
        'vessel': str,
        'method': str,
        'sample_volume': float,
        'dilution_volume': float,
        'dilution_solvent': str,
        'instrument': str,
        'on_finish': Callable[[str], Union[Callable[['AbstractSpectrum'], None], None]],
        'reference_step': JSON_PROP_TYPE,
        'method_properties': JSON_PROP_TYPE,
        'on_finish_arg': str,
        # method related
        'cleaning_solvent': str,
        'cleaning_solvent_vessel': str,
        'priming_waste': str,
        # sample related
        'sample_pump': str,
        'injection_pump': str,
        'sample_excess_volume': float,
        'dilution_vessel': str,
        'dilution_solvent_vessel': str,
        'injection_waste': str,
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
        'on_finish_arg',
    ]

    DEFAULT_PROPS = {
        # anonymous function to take a string argument
        # and return a new callable
        'on_finish': lambda arg: lambda spec: None,
        # volume left in the syringe after sample is injected
        'sample_excess_volume': 2,
        'method_props': {},
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
        on_finish_arg: Optional[str] = None,
        **kwargs
    ) -> None:
        super().__init__(locals())

        self.validate_props()

    def validate_props(self):
        """Validates given step properties.

        E.g. if dilution volume is given -> dilution solvent must be chosen.

        Validation is unique for a given instrument and is normally extended in
        an ancestor class.
        """

        # Validating cleaning solvent is given
        validate_cleaning(
            sample_volume=self.sample_volume,
            dilution_volume=self.dilution_volume,
            cleaning_solvent=self.cleaning_solvent
        )

        # Validating dilution solvent is given
        validate_dilution(
            dilution_volume=self.dilution_volume,
            dilution_solvent=self.dilution_solvent
        )

    def on_prepare_for_execution(self, graph: 'MultiDiGraph') -> None:
        """Necessary preparations before step may be executed."""

        if self.method == 'interactive':
            # nothing needed if running the analysis "interactively"
            return

        self.instrument = find_instrument(graph, self.method)

        if self.sample_volume:
            self._prepare_for_sampling(graph=graph)

        if self.dilution_volume:
            self._prepare_for_dilution(graph=graph)

    def _prepare_for_sampling(self, graph: 'MultiDiGraph') -> None:
        """Necessary preparations if sampling is required."""
        # Nearest pump needed to store "buffer" of the sample volume
        self.injection_pump = get_nearest_node(
            graph=graph,
            src=self.instrument,
            target_vessel_class=CHEMPUTER_PUMP
        )

        injection_pump_max_volume = get_pump_max_volume(
            graph=graph,
            aspiration_pump=self.injection_pump
        )

        # Reducing if the desired volume exceeds the pump's max volume
        if (self.sample_excess_volume + self.sample_volume >
        injection_pump_max_volume):
            self.sample_excess_volume = \
                injection_pump_max_volume - self.sample_volume

        # Obtaining cleaning solvent vessel
        self.cleaning_solvent_vessel = get_reagent_vessel(
            graph,
            self.cleaning_solvent
        )

        # Obtaining nearest waste to dispose sample after priming
        self.priming_waste = get_nearest_node(
            graph=graph,
            src=self.vessel,
            target_vessel_class=CHEMPUTER_WASTE
        )

        # Obtaining nearest waste to dispose sample before injection
        self.injection_waste = get_nearest_node(
            graph=graph,
            src=self.instrument,
            target_vessel_class=CHEMPUTER_WASTE
        )

    def _prepare_for_dilution(self, graph: 'MultiDiGraph') -> None:
        """Necessary preparations if dilution is required."""

    @abstractmethod
    def get_preparation_steps(self):
        """Gets steps required to prepare the mixture prior to analysis.

        Preparation steps are unique depending on the initial material location
        e.g. filter/flask/reactor and analytical instrument in use.

        Such steps might include: cooling reaction mixture; dissolving
        precipitate; drying material; etc.

        RESERVED FOR FUTURE USE!
        """

    @abstractmethod
    def get_analysis_steps(self):
        """Gets steps required to acquire the analytical data.

        Steps are unique for the given instrument.
        """

    @abstractmethod
    def get_postanalysis_steps(self):
        """Gets steps required after the data's been acquired.

        Steps are unique for the given instrument.
        """

    def get_sampling_steps(self):
        """Gets steps required to acquire the sample.

        Basically a given volume + some access is transferred to the syringe
        and slowly injected into the instrument.
        """

    def get_cleaning_steps(self):
        """Gets steps required to clean the instrument (and dilution vessel).
        """
