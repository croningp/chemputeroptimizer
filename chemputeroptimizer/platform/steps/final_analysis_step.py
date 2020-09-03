from typing import List, Callable, Optional, Dict, Any

from networkx import MultiDiGraph

from xdl.errors import XDLError
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

from .steps_analysis import RunRaman, RunNMR
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
        'dilution_vessel': str,
        'method': str,
        'sample_volume': int,
        'dilution_volume': int,
        'dilution_solvent': str,
        'instrument': str,
        'distribution_valve': str,
        'on_finish': Any,
        'reference_step': Step,
    }

    INTERNAL_PROPS = [
        'instrument',
        'reference_step',
        #'cleaning_solvent',
        #'nearest_waste',
    ]

    def __init__(
            self,
            vessel: str,
            method: str,
            sample_volume: Optional[int] = None,
            on_finish: Optional[Any] = None,

            # Internal properties
            instrument: Optional[str] = None,
            reference_step: Optional[Step] = None,
            #cleaning_solvent: Optional[str] = None,
            #nearest_waste: Optional[str] = None,
            **kwargs
        ) -> None:
        super().__init__(locals())

        # check if method is valid
        if method not in SUPPORTED_ANALYTICAL_METHODS:
            raise OptimizerError(f'Specified method {method} is not supported')

    def on_prepare_for_execution(self, graph: MultiDiGraph) -> None:

        if self.method != 'interactive':
            self.instrument = find_instrument(graph, self.method)

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

        # TODO add implied steps for additional analytical methods
        # HPLC, NMR, pH

        return []
