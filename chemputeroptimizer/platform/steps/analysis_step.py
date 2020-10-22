"""
Optimizer/XDL step to perform the analysis of the mixture in a given vessel.
Contains all necessary methods to construct a complete step depending on the
analytical method and the target vessel.
"""

from typing import Any, Optional, List, Callable

from networkx import MultiDiGraph

from xdl.constants import JSON_PROP_TYPE
from xdl.steps.base_steps import AbstractStep, Step
from xdl.steps.special_steps import Callback, Repeat

from chemputerxdl.utils.execution import (
    get_nearest_node,
    get_reagent_vessel,
)
from chemputerxdl.steps import (
    Transfer,
    Wait,
    HeatChill,
    HeatChillToTemp,
    Wait,
    Stir,
)

from .steps_analysis import RunNMR, RunRaman
from .utils import find_instrument
from ...utils.errors import OptimizerError
from ...constants import (
    SUPPORTED_ANALYTICAL_METHODS,
)


NO_PREPARATION_STEPS = [
    'HeatChill',
    'HeatChillToTemp',
    'Wait',
    'Stir',
]

class Analyze(AbstractStep):
    """A generic step to perform an analysis of the chemicals in a given vessel

    Args:
        vessel (str): Name of the vessel (on the graph) where the analyte is.
        method (str): Name of the analytical method for the material analysis.
            Will determine necessary steps to perform the analysis.
        sample_volume (int): Volume of the product sample to be sent to the
            analytical instrument. Either given, or determined in the graph.
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

        # check if method is valid
        if method not in SUPPORTED_ANALYTICAL_METHODS:
            raise OptimizerError(f'Specified method {method} is not supported')

        super().__init__(locals())

    def on_prepare_for_execution(self, graph: MultiDiGraph) -> None:

        if self.method == 'interactive':
            # nothing needed if running the analysis "interactively"
            return

        self.instrument = find_instrument(graph, self.method)

        # Nearest pump needed to store "buffer" of the sample volume
        self.injection_pump = get_nearest_node(
            graph=graph,
            src=self.instrument,
            target_vessel_class='ChemputerPump'
        )

        # Accessing target properties, so storing a graph object instead
        injection_pump_obj = graph.nodes[self.injection_pump]

        # Reducing if the desired volume exceeds the pump's max volume
        if self.sample_transfer_volume + self.sample_volume > \
            injection_pump_obj['max_volume']:
            self.sample_transfer_volume = injection_pump_obj['max_volume'] - \
                self.sample_volume

        # Obtain cleaning solvent vessel
        self.cleaning_solvent_vessel = get_reagent_vessel(
            graph,
            self.cleaning_solvent
        )

        # Obtaining nearest waste to dispose solvent after cleaning
        self.nearest_waste = get_nearest_node(
            graph=graph,
            src=self.instrument,
            target_vessel_class='ChemputerWaste'
        )

    def get_steps(self) -> List[Step]:
        steps = []

        # Preparation after the reference step
        steps.extend(self._get_preparation_steps())

        steps.extend(self._get_analytical_steps())

        # Appending steps needed for cleaning
        if self.cleaning_solvent is not None:
            steps.extend(self._get_cleaning_steps())

        return steps

    def _get_preparation_steps(self) -> List[Step]:
        """ Obtain steps necessary to prepare the analyte according to the
            reference step. """

        steps = []

        # if no reference step given - return empty list
        if self.reference_step is None:
            return steps

        # reaction is complete and reaction product
        # remains in reaction vessel
        if self.reference_step['step'] in NO_PREPARATION_STEPS:
            try:
                # checking for steps temperature
                if not 18 <= self.reference_step['properties']['temp'] <= 30:
                    raise OptimizerError(
                        'Final analysis only supported for room temperature \
reaction mixture!')
            except KeyError: # no temperature for the step, i.e. Stir
                pass

        # TODO support other steps wrapped with FinalAnalysis, i.e. Filter, Dry
        # required additional preparation of the sample, e.g. dissolution

        return steps

    def _get_analytical_steps(self) -> List[Step]:
        """
        Obtaining steps to perform analysis based on internal method attribute
        """

        if self.method == 'interactive':
            return [
                Callback(
                    fn=self.on_finish,
                )
            ]

        # Raman
        # no special prepartion needed, just measure the spectrum
        if self.method == 'Raman':
            return [
                RunRaman(
                    raman=self.instrument,
                    on_finish=self.on_finish,
                )
            ]

        # NMR
        # take sample and send it to instrument, clean up afterwards
        if self.method == 'NMR':
            return self._get_nmr_steps()

        # TODO add implied steps for additional analytical methods
        # HPLC, NMR, pH

        return []

    def _get_nmr_steps(self) -> List:
        """ Returns the steps relevant for NMR analysis execution. """

        return [
            # Transferring to the injection pump first
            Transfer(
                from_vessel=self.vessel,
                to_vessel=self.injection_pump,
                volume=self.sample_transfer_volume + self.sample_volume,
                aspiration_speed=10,
            ),
            # Injecting into the instrument
            Transfer(
                from_vessel=self.injection_pump,
                to_vessel=self.instrument,
                volume=self.sample_volume,
                aspiration_speed=10,
                dispense_speed=10,
            ),
            # Returning the excess back to the vessel
            Transfer(
                from_vessel=self.injection_pump,
                to_vessel=self.vessel,
                volume=self.sample_transfer_volume,
            ),
            # Running the instrument
            RunNMR(
                nmr=self.instrument,
                on_finish=self.on_finish,
                **self.method_props,
            ),
            # Transferring the sample volume (+extra 20%) back to the vessel
            Transfer(
                from_vessel=self.instrument,
                to_vessel=self.vessel,
                volume=self.sample_volume*1.2, # 20% extra
                aspiration_speed=5,
            ),
        ]

    def _get_cleaning_steps(self):

        if self.method == 'Raman':
            # Contactless probe using, no cleaning required
            return []

        if self.method == 'NMR':
            # Flush the nmr cell with the cleaning solvent
            cleaning_steps = [
                Transfer(
                    from_vessel=self.cleaning_solvent_vessel,
                    to_vessel=self.instrument,
                    volume=self.sample_volume*1.5,
                    dispense_speed=5,
                ),
                Wait(
                    time=120,
                ),
                Transfer(
                    from_vessel=self.instrument,
                    to_vessel=self.nearest_waste,
                    volume=self.sample_volume*2,
                    aspiration_speed=5,
                ),
            ]

            # Repeat cleaning twice
            return [Repeat(children=cleaning_steps, repeats=2)]
