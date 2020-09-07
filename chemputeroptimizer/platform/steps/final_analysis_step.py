from typing import List, Callable, Optional, Dict, Any

from networkx import MultiDiGraph

from xdl.errors import XDLError
from xdl.steps.base_steps import AbstractStep, Step
from xdl.steps.special_steps import Callback
from chemputerxdl.utils.execution import get_nearest_node
from chemputerxdl.steps import (
    CleanBackbone,
    CleanVessel,
    PrimePumpForAdd,
    HeatChill,
    HeatChillToTemp,
    Wait,
    StopHeatChill,
    Transfer,
    Dissolve,
    Stir,
    Add,
    CMove,
)

from .steps_analysis import RunRaman, RunNMR, RunHPLC
from .utils import find_instrument, find_nearest_waste
from ...utils import SpectraAnalyzer
from ...utils.errors import OptimizerError
from ...constants import (
    SUPPORTED_ANALYTICAL_METHODS,
    SUPPORTED_FINAL_ANALYSIS_STEPS,
)


class FinalAnalysis(AbstractStep):
    """Support for a step to obtain final yield and purity. Should be used
    after the last step of the procedure where pure material is obtained.

    Steps supported:
        Stir: reaction is over and product remains in a reaction vessel.
        HeatChill/HeatChillToTemp: reaction is over and product remains in a
            reaction vessel (only at or near room temperature).

    Args:
        vessel (str): Name of the vessel (on the graph) where final product
            remains at the end of the reaction.
        dilution_vessel (str): Name of the vessel to which the sample transfered 
            and in which it gets diluted. Currently only needed for HPLC.
        method (str): Names of the analytical method for material
            analysis, e.g. Raman, NMR, HPLC, etc. Will determine necessary steps
            to obtain analytical data, e.g. if sampling is required.
        sample_volume (int): Volume of product sample to be sent to the
            analytical instrument. Either supplied, or determined in the graph.
        dilution_volume (int): Volume of dilution solvent  used to dilute sample
            to be sent to the analytical instrument. Currently only needed for HPLC.
        dilution_solvent (str): Solvent used to dilute sample to be sent to the 
            analytical instrument. Currently only needed for HPLC. Typically MeCN.
        distribution_valve (str): Distribution valve (IDEX) used to trigger the HPLC.
            Currently only needed for HPLC.
    """

    PROP_TYPES = {
        'vessel': str,
        'method': str,
        'method_props': Dict,
        'sample_volume': int,
        'dilution_vessel': str,
        'dilution_volume': int,
        'dilution_solvent': str,
        'instrument': str,
        'distribution_valve': str,
        'injection_pump': str,
        'on_finish': Any,
        'reference_step': Step,
    }

    INTERNAL_PROPS = [
        'instrument',
        'reference_step',
        'distribution_valve',
        'injection_pump'
        #'cleaning_solvent',
        'nearest_waste',
    ]

    def __init__(
            self,
            vessel: str,
            method: str,
            method_props: Dict,
            sample_volume: Optional[int] = None,
            dilution_vessel: Optional[str]= None,
            dilution_volume: Optional[int]= None,
            dilution_solvent: Optional[str]= None,
            on_finish: Optional[Any] = None,

            # Internal properties
            instrument: Optional[str] = None,
            reference_step: Optional[Step] = None,
            #cleaning_solvent: Optional[str] = None,
            distribution_valve: Optional[str] = None,
            injection_pump: Optional[str] = None,
            nearest_waste: Optional[str] = None,
            **kwargs
        ) -> None:
        super().__init__(locals())

        # check if method is valid
        if method not in SUPPORTED_ANALYTICAL_METHODS:
            raise OptimizerError(f'Specified method {method} is not supported')

        if method == 'HPLC' and dilution_volume < 5:
                raise OptimizerError(f'Dilution volume for HPLC analysis must be at least 5 mL.')

    def on_prepare_for_execution(self, graph: MultiDiGraph) -> None:

        if self.method != 'interactive':
            self.instrument = find_instrument(graph, self.method)

        if self.method == 'HPLC':
            self.distribution_valve = find_instrument(graph, "IDEX")
            self.nearest_waste = get_nearest_node(graph, self.dilution_vessel, "ChemputerWaste")
            self.injection_pump = get_nearest_node(graph, self.dilution_vessel, "ChemputerIDEX")

    def get_steps(self) -> List[Step]:
        steps = []

        # reaction is complete and reaction product
        # remains in reaction vessel
        if isinstance(self.reference_step,
                      (HeatChill, HeatChillToTemp, Wait, Stir)):
            try:
                # checking for steps temperature
                if not 18 <= self.reference_step.temp <= 30:
                    raise OptimizerError(
                        'Final analysis only supported for room temperature \
reaction mixture!')
            except AttributeError:
                pass

        steps.extend(self._get_analytical_steps())

        # TODO support other steps wrapped with FinalAnalysis, i.e. Filter, Dry
        # required additional preparation of the sample, e.g. dissolution

        return steps

    def _get_analytical_steps(self) -> List:
        """Obtaining steps to perform analysis based on internal method attribute"""

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
            return [
                Transfer(
                    from_vessel=self.vessel,
                    to_vessel=self.instrument,
                    volume=self.sample_volume,
                    aspiration_speed=10,
                    dispense_speed=10,
                ),
                RunNMR(
                    nmr=self.instrument,
                    on_finish=self.on_finish,
                ),
                Transfer(
                    from_vessel=self.instrument,
                    to_vessel=self.vessel,
                    volume=self.sample_volume,
                    aspiration_speed=10,
                    dispense_speed=10,
                ),
            ]

        # HPLC
        # take sample, dilute
        if self.method == 'HPLC':
            return self._get_hplc_steps()

        # TODO add implied steps for additional analytical methods
        # pH

    def _get_hplc_steps(self) -> List:
        return [
            # clean backbone
            CleanBackbone(
                solvent=self.dilution_solvent
            ),
            # prime tube
            PrimePumpForAdd(
                reagent="", 
                reagent_vessel=self.vessel, 
                volume=1
            ),
            # transfer sample to dilution vessel
            Transfer(
                from_vessel=self.vessel,
                to_vessel=self.dilution_vessel,
                volume=self.sample_volume,
                aspiration_speed=10,
                dispense_speed=10,
            ),
            # add solvent to dilution vessel (with stirring)
            Add(
                reagent=self.dilution_solvent,
                vessel=self.dilution_vessel,
                volume=self.dilution_volume,
                stir=True
            ),
            # wait
            Wait(
                time=60
            ),
            # move to pump
            CMove(
                from_vessel=self.dilution_vessel,
                to_vessel=self.injection_pump,
                volume=5, # dilution volume must be > 5
                aspiration_speed=10
            ),
            # move to idex (slowly)
            CMove(
                from_vessel=self.injection_pump,
                to_vessel=self.distribution_valve,
                volume=2.5,
                dispense_speed=0.5
            ),
            # RunHPLC(method="default")
            RunHPLC(
                hplc=self.instrument,
                valve=self.valve,
                protocol=self.method_props['run_method'],
                on_finish=self.on_finish,
             ),
            # move rest of volume in pump to waste
            CMove(
                from_vessel=self.injection_pump,
                to_vessel=self.nearest_waste,
                volume=2.5
            ),
            # Clean dilution flask
            CleanVessel(
                vessel=self.dilution_vessel, 
                solvent=self.dilution_solvent,
                volume=self.dilution_volume,
                repeats=3
            ),
            # Clean sample loop
            CMove(
                from_vessel=self.dilution_solvent,
                to_vessel=self.distribution_valve,
                volume=5,
                dispense_speed=0.5
            ),
            # move acetonitrile to pump for blank run
            CMove(
                from_vessel=self.dilution_solvent,
                to_vessel=self.injection_pump,
                volume=5,
                aspiration_speed=10
            ),
            # move to idex (slowly) for blank run
            CMove(
                from_vessel=self.injection_pump,
                to_vessel=self.distribution_valve,
                volume=2.5,
                dispense_speed=0.5
            ),
            # RunHPLC(method="cleaning")
            RunHPLC(
                hplc=self.instrument,
                valve=self.valve,
                protocol=self.method_props['cleaning_method'],
                on_finish=self.on_finish,
             ),
            # move rest of volume in pump to waste
            CMove(
                from_vessel=self.injection_pump,
                to_vessel=self.nearest_waste,
                volume=2.5
            ),
        ]
