"""
Optimizer/XDL step to perform the analysis of the mixture in a given vessel.
Contains all necessary methods to construct a complete step depending on the
analytical method and the target vessel.
"""

from typing import Any, Optional, List, Callable

from networkx import MultiDiGraph

from xdl.constants import JSON_PROP_TYPE
from xdl.steps.base_steps import AbstractStep, Step
from xdl.steps.special_steps import Callback, Repeat, Await, Async

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
    CleanBackbone,
    PrimePumpForAdd,
    Add,
    CleanVessel,
    Unlock
)

from chemputerxdl.steps.base_step import ChemputerStep

from .steps_analysis import RunNMR, RunRaman, RunHPLC
from .steps_analysis.shim_nmr import ShimNMR, check_last_shimming_results
from .utils import (
    find_instrument,
    get_dilution_flask,
    find_shimming_solvent_flask,
)
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

# sample constants
PRIMING_WASTE_VOLUME = 1 # to prime the tubing while acquiring sample
DISSOLUTION_TIME = 60 # seconds
NMR_CLEANING_DELAY = 120 # seconds
HPLC_INJECTION_VOLUME = 2.5 # ml
HPLC_INJECTION_EXCESS_VOLUME = 2 # ml
HPLC_SAMPLE_LOOP_CLEANING_VOLUME = 5 # ml

# speed constants
SAMPLE_SPEED_MEDIUM = 10
SAMPLE_SPEED_SLOW = 5
HPLC_INJECTION_SPEED = 0.5


class Analyze(ChemputerStep, AbstractStep):
    """A generic step to perform an analysis of the chemicals in a given vessel

    Args:
        vessel (str): Name of the vessel (on the graph) where the analyte is.
        method (str): Name of the analytical method for the material analysis.
            Will determine necessary steps to perform the analysis.
        sample_volume (int): Volume of the product sample to be sent to the
            analytical instrument. Either given, or determined in the graph.
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
        'injection_pump': str,
        'sample_excess_volume': float,
        'dilution_vessel': str,
        'dilution_volume': float,
        'dilution_solvent': str,
        'dilution_solvent_vessel': str,
        'distribution_valve': str,
        'injection_waste': str,
        # NMR specific
        'force_shimming': bool,
        'shimming_solvent_flask': str,
        'shimming_reference_peak': float, # for correct shimming
    }

    INTERNAL_PROPS = [
        'instrument',
        'reference_step',
        'priming_waste',
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

        # check if method is valid
        if method not in SUPPORTED_ANALYTICAL_METHODS:
            raise OptimizerError(f'Specified method {method} is not supported')

        if (method == 'HPLC'
                and dilution_volume is not None
                and dilution_volume < 5):
            raise OptimizerError('Dilution volume must be at least 5 ml for\
HPLC analysis.')

        # additional check for dilution solvent attribute
        if dilution_volume is not None and dilution_solvent is None:
            raise OptimizerError('Dilution solvent must be specified if volume\
is given.')


        super().__init__(locals())

        if method not in ['interactive', 'Raman'] and self.cleaning_solvent is None:
            raise OptimizerError('Cleaning solvent must be given if not \
running in interactive mode!')

    def on_prepare_for_execution(self, graph: MultiDiGraph) -> None:

        if self.method == 'interactive':
            # nothing needed if running the analysis "interactively"
            return

        self.instrument = find_instrument(graph, self.method)

        if self.sample_volume is not None:
            # Nearest pump needed to store "buffer" of the sample volume
            self.injection_pump = get_nearest_node(
                graph=graph,
                src=self.instrument,
                target_vessel_class='ChemputerPump'
            )

            # Accessing target properties, so storing a graph object instead
            injection_pump_obj = graph.nodes[self.injection_pump]

            # Reducing if the desired volume exceeds the pump's max volume
            if self.sample_excess_volume + self.sample_volume > \
                injection_pump_obj['max_volume']:
                self.sample_excess_volume = \
                    injection_pump_obj['max_volume'] - self.sample_volume

        # Obtaining cleaning solvent vessel
        self.cleaning_solvent_vessel = get_reagent_vessel(
            graph,
            self.cleaning_solvent
        )

        # Obtaining nearest waste to dispose sample after priming
        self.priming_waste = get_nearest_node(
            graph=graph,
            src=self.vessel,
            target_vessel_class='ChemputerWaste'
        )

        # Obtaining nearest waste to dispose sample before injection
        self.injection_waste = get_nearest_node(
            graph=graph,
            src=self.instrument,
            target_vessel_class='ChemputerWaste'
        )

        # Updating if dilution is needed
        if self.dilution_volume is not None:
            self.dilution_solvent_vessel = get_reagent_vessel(
                graph,
                self.dilution_solvent
            )

            self.dilution_vessel = get_dilution_flask(graph)
            if self.dilution_vessel is None:
                raise OptimizerError('Dilution vessel is not found on graph!')

        # Additional preparations for HPLC
        if self.method == 'HPLC':
            self.distribution_valve = find_instrument(graph, 'IDEX')

        # Additional preparations for NMR
        if self.method == 'NMR':
            self.nmr_precheck(graph)

    def get_steps(self) -> List[Step]:
        steps = []

        # Preparation after the reference step
        steps.extend(self._get_preparation_steps())

        # Actual analysis
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

        # Shimming
        if self.method == 'NMR' and self.force_shimming:
            steps.extend(self._get_shimming_steps())

        # additional preparations if dilution is specified
        if self.dilution_volume is not None:
            steps.extend([
                # clean backbone before
                CleanBackbone(
                    solvent=self.dilution_solvent
                ),
                # prime tubing
                # FIXME
                PrimePumpForAdd(
                    reagent='',
                    reagent_vessel=self.vessel,
                    waste_vessel=self.priming_waste,
                    volume=PRIMING_WASTE_VOLUME,
                ),
                # transferring sample
                Transfer(
                    from_vessel=self.vessel,
                    to_vessel=self.dilution_vessel,
                    volume=self.sample_volume,
                    aspiration_speed=SAMPLE_SPEED_MEDIUM,
                    dispense_speed=SAMPLE_SPEED_MEDIUM,
                ),
                # diluting
                Add(
                    reagent=self.dilution_solvent,
                    vessel=self.dilution_vessel,
                    volume=self.dilution_volume,
                    stir=True
                ),
                # wait
                Wait(
                    time=DISSOLUTION_TIME
                )
            ])

        return steps

    def _get_analytical_steps(self) -> List[Step]:
        """
        Obtaining steps to perform analysis based on internal method attribute
        """

        if self.method == 'interactive':
            return [
                Callback(
                    fn=self.on_finish(self.batch_id),
                )
            ]

        # Raman
        # no special prepartion needed, just measure the spectrum
        if self.method == 'Raman':
            return [
                RunRaman(
                    raman=self.instrument,
                    on_finish=self.on_finish(self.batch_id),
                    **self.method_props
                )
            ]

        # NMR
        # take sample and send it to instrument, clean up afterwards
        if self.method == 'NMR':
            return self._get_nmr_steps()

        if self.method == 'HPLC':
            return self._get_hplc_steps()

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
                volume=self.sample_excess_volume + self.sample_volume,
                aspiration_speed=SAMPLE_SPEED_MEDIUM,
            ),
            # Injecting into the instrument
            Transfer(
                from_vessel=self.injection_pump,
                to_vessel=self.instrument,
                volume=self.sample_volume,
                aspiration_speed=SAMPLE_SPEED_MEDIUM,
                dispense_speed=SAMPLE_SPEED_MEDIUM,
            ),
            # Returning the excess back to the vessel
            Transfer(
                from_vessel=self.injection_pump,
                to_vessel=self.vessel,
                volume=self.sample_excess_volume,
            ),
            # Running the instrument
            RunNMR(
                nmr=self.instrument,
                on_finish=self.on_finish(self.batch_id),
                **self.method_props,
            ),
            # Transferring the sample volume (+extra 20%) back to the vessel
            Transfer(
                from_vessel=self.instrument,
                to_vessel=self.vessel,
                volume=self.sample_volume*1.2, # 20% extra
                aspiration_speed=SAMPLE_SPEED_SLOW,
            ),
        ]

    def _get_shimming_steps(self) -> List:
        """Return steps needed to perform the NMR shimming."""

        return [
                Transfer(
                    from_vessel=self.shimming_solvent_flask,
                    to_vessel=self.injection_pump,
                    volume=self.sample_excess_volume + self.sample_volume,
                    aspiration_speed=SAMPLE_SPEED_MEDIUM,
                ),
                # Injecting into the instrument
                Transfer(
                    from_vessel=self.injection_pump,
                    to_vessel=self.instrument,
                    volume=self.sample_volume,
                    aspiration_speed=SAMPLE_SPEED_MEDIUM,
                    dispense_speed=SAMPLE_SPEED_MEDIUM,
                ),
                # Discarding excess
                Transfer(
                    from_vessel=self.injection_pump,
                    to_vessel=self.injection_waste,
                    volume=self.sample_excess_volume,
                ),
                # Running the instrument
                ShimNMR(
                    nmr=self.instrument,
                    reference_peak=self.shimming_reference_peak,
                ),
                # Discarding sample
                Transfer(
                    from_vessel=self.instrument,
                    to_vessel=self.injection_waste,
                    volume=self.sample_volume*2, # twice excess to remove all
                    aspiration_speed=SAMPLE_SPEED_SLOW,
                ),
                # Repeat again
                Transfer(
                    from_vessel=self.instrument,
                    to_vessel=self.injection_waste,
                    volume=self.sample_volume*2, # twice excess to remove all
                    aspiration_speed=SAMPLE_SPEED_SLOW,
                ),
            ]

    def _get_hplc_steps(self) -> List:
        """ Return steps relevant for the HPLC analysis.

        Assuming that analyte was diluted and now stored in dilution_vessel.
        """
        return [
            # Transfer to injection pump
            Transfer(
                from_vessel=self.dilution_vessel,
                to_vessel=self.injection_pump,
                # hardcoded for now, might be changed in the future
                # to cover dilution case with various analytical techniques
                volume=HPLC_INJECTION_EXCESS_VOLUME + HPLC_INJECTION_VOLUME,
                aspiration_speed=SAMPLE_SPEED_MEDIUM
            ),
            # Charging distribution valve
            Transfer(
                from_vessel=self.injection_pump,
                to_vessel=self.distribution_valve,
                volume=HPLC_INJECTION_VOLUME,
                dispense_speed=HPLC_INJECTION_SPEED,
            ),
            # Running analysis
            Async(
                pid="HPLC",
                children=[
                    RunHPLC(
                        hplc=self.instrument,
                        valve=self.distribution_valve,
                        on_finish=self.on_finish(self.batch_id),
                        **self.method_props
                    ),
                ]
            ),
            # Discarding the rest
            Transfer(
                from_vessel=self.injection_pump,
                to_vessel=self.injection_waste,
                # what's charged - what's injected
                volume=HPLC_INJECTION_EXCESS_VOLUME
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
                    dispense_speed=SAMPLE_SPEED_SLOW,
                ),
                Wait(
                    time=NMR_CLEANING_DELAY,
                ),
                Transfer(
                    from_vessel=self.instrument,
                    to_vessel=self.priming_waste,
                    volume=self.sample_volume*2,
                    aspiration_speed=SAMPLE_SPEED_SLOW,
                ),
            ]

            return [
                # Repeat cleaning twice
                Repeat(children=cleaning_steps, repeats=2),
                # Unlock all associated nodes
                Unlock(
                    nodes=[
                        self.instrument,
                        self.injection_pump,
                        self.cleaning_solvent_vessel,
                        self.vessel,
                    ]
                )
            ]

        if self.method == 'HPLC':
            return [
                # Cleaning dilution flask
                Transfer(
                    from_vessel=self.dilution_vessel,
                    to_vessel=self.injection_waste,
                    # FIXME use "all" here
                    # atm "all" doesn't get updated to the actual volume
                    volume=self.dilution_volume + self.sample_excess_volume +\
                        self.sample_volume,
                ),
                CleanVessel(
                    vessel=self.dilution_vessel,
                    solvent=self.cleaning_solvent,
                    volume=self.dilution_volume + self.sample_excess_volume +\
                        self.sample_volume,
                    repeats=3,
                    dry=False,
                    temp=None,
                ),
                # Clean sample loop
                Transfer(
                    from_vessel=self.dilution_solvent_vessel,
                    to_vessel=self.distribution_valve,
                    volume=HPLC_SAMPLE_LOOP_CLEANING_VOLUME,
                    dispense_speed=HPLC_INJECTION_SPEED
                ),
                # Prepare blank run
                Transfer(
                    from_vessel=self.dilution_solvent_vessel,
                    to_vessel=self.injection_pump,
                    volume=HPLC_SAMPLE_LOOP_CLEANING_VOLUME,
                    aspiration_speed=SAMPLE_SPEED_MEDIUM
                ),
                # Preparing for blank run
                Transfer(
                    from_vessel=self.injection_pump,
                    to_vessel=self.distribution_valve,
                    volume=HPLC_INJECTION_VOLUME,
                    dispense_speed=HPLC_INJECTION_SPEED,
                ),
                # wait for HPLC analysis to finish
                Await(
                    pid="HPLC"
                ),
                # blank run
                RunHPLC(
                    hplc=self.instrument,
                    valve=self.distribution_valve,
                    on_finish=self.on_finish(self.batch_id),
                    is_cleaning=True,
                    **self.method_props
                ),
                # Discarding the rest
                Transfer(
                    from_vessel=self.injection_pump,
                    to_vessel=self.injection_waste,
                    volume=HPLC_SAMPLE_LOOP_CLEANING_VOLUME - \
                        HPLC_INJECTION_VOLUME
                ),
                Unlock(
                    nodes=[
                        self.injection_pump,
                        self.distribution_valve,
                        self.dilution_vessel]
                )
            ]

        # for the interactive analysis
        return []

    def nmr_precheck(self, graph: MultiDiGraph) -> None:
        """ Additional checks needed for the NMR analysis.
        """

        shimming_solvent_flask, reference_peak = \
            find_shimming_solvent_flask(graph)

        # Light check
        try:
            assert shimming_solvent_flask
        except AssertionError:
            self.logger.critical('Found no solvents suitable for shimming the \
NMR. If the procedure is longer than 24 hours shimming will be required!')

        # Checking for the last shimming
        if not check_last_shimming_results() or self.force_shimming:
            # If shimming is required, but no suitable solvents found
            if shimming_solvent_flask is None:
                raise OptimizerError('No solvents suitable for shimming the \
NMR found, but shimming is required!')
            # Else force shimming
            self.force_shimming = True

        # If all okay -> setup the step attributes
        self.shimming_solvent_flask = shimming_solvent_flask
        self.shimming_reference_peak = reference_peak
