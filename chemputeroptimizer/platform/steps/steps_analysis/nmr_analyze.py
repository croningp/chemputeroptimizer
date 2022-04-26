"""
High-level XDL step to run the analysis with NMR.

Current implementation relays on AnalyticalLabware interface for the benchtop
Spinsolve NMR. For any details check the manual.
"""

# pylint: disable=unused-argument,attribute-defined-outside-init, super-init-not-called

import typing
import warnings
from typing import Optional, Callable, Union

from xdl.constants import JSON_PROP_TYPE
from xdl.steps.base_steps import AbstractStep

from chemputerxdl.steps import (
    CMove,
)

from ..steps_sample import InjectSample
from ..steps_analytical_instruments import RunNMR, ShimNMR
from ..steps_analytical_instruments.utils import (
    check_last_shimming_results,
    find_shimming_solvent_flask,
    ShimmingRequired,
    NoShimmingSolvent,
)

from .abstract_analyze import AbstactAnalyzeStep

if typing.TYPE_CHECKING:
    from AnalyticalLabware.devices.chemputer_devices import AbstractSpectrum
    from networkx import MultiDiGraph
    from xdl.steps.base_steps import Step


# Excess to discard the sample
SAMPLE_DISCARD_EXCESS = 2  # 200%
SAMPLE_MOVE_EXCESS = 1.2  # 120%

class NMRAnalyze(AbstactAnalyzeStep, AbstractStep):
    """High-level XDL step to analyze a sample with NMR.

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
        method_props (dict): Dictionary with additional properties, passed to
            the low-level analysis step.
        on_finish (Callable[[str], Callable]): Callback function to execute
            when analysis is performed. This function should accept a string
            argument and return a new callable -> the one which is passed to
            the low-level analytical step and executed with a spectrum as an
            argument.
        on_finish_arg (str): Argument for the on_finish callback factory.
        reference_step (dict): Properties from the "reference" step, that
            dictates the necessary preparations before the analysis. E.g.,
            cooling reaction mixture from previous HeatChill step.
        dilution_vessel (str): Name of the container to dilute the sample.
            Must have a stirrer, otherwise sample dilution is not guaranteed.
            If not given -> locate first empty flask with stirrer on the graph.

    NMR specific args:
        force_shimming (bool): If the shimming must be performed before each
            analysis. Defaults to False.
        shimming_solvent_flask (str): Flask containing solvent suitable for
            shimming. Given internally. If no suitable solvent found - an
            exception is raised.
        shimming_reference_peak (float): Peak position for the shimming
            solvent. Given internally.

    Attrs aka INTERNAL_PROPS:
        instrument (str): Name of the analytical instrument on graph.
        cleaning_solvent_vessel (str): Name of the cleaning solvent vessel on
            the graph.
        dilution_solvent_vessel (str): Name of the dilution solvent vessel on
            the graph.
        analyte_vessel (str): Name of the vessel containing the analyte. Is
            updated depending on the sample preparations, i.e. if dilution is
            required -> `analyte_vessel` = `dilution_vessel`.
        injection_waste (str): Name of the vessel to dump sample excess. Given
            internally.
    """

    INJECTION_SPEED = 5  # mL/min

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
        'method_props': JSON_PROP_TYPE,
        'on_finish_arg': str,
        # method related
        'cleaning_solvent': str,
        'cleaning_solvent_vessel': str,
        # sample related
        'dilution_vessel': str,
        'dilution_solvent_vessel': str,
        'analyte_vessel': str,
        # NMR specific
        'force_shimming': bool,
        'shimming_solvent_flask': str,
        'shimming_reference_peak': float,
        'injection_waste': str,
    }

    INTERNAL_PROPS = [
        'instrument',
        'reference_step',
        'cleaning_solvent_vessel',
        'dilution_vessel',
        'dilution_solvent_vessel',
        'on_finish',
        'on_finish_arg',
        'analyte_vessel',
        'shimming_solvent_flask',
        'shimming_reference_peak',
        'injection_waste',
    ]

    DEFAULT_PROPS = {
        # anonymous function to take a string argument
        # and return a new callable
        'on_finish': lambda arg: lambda spec: None,
        'method_props': {},
        'force_shimming': False,
        'method': 'NMR',
    }

    def __init__(
        self,
        vessel: str,
        sample_volume: float,
        method: Optional[str] = 'default',
        cleaning_solvent: Optional[str] = None,
        on_finish: Optional[Callable] = 'default',
        method_props: JSON_PROP_TYPE = 'default',
        dilution_volume: Optional[float] = None,
        dilution_solvent: Optional[str] = None,
        # Internal properties
        instrument: Optional[str] = None,
        reference_step: Optional[JSON_PROP_TYPE] = None,
        cleaning_solvent_vessel: Optional[str] = None,
        dilution_solvent_vessel: Optional[str] = None,
        dilution_vessel: Optional[str] = None,
        on_finish_arg: Optional[str] = None,
        analyte_vessel: Optional[str] = None,
        injection_waste: Optional[str] = None,
        # NMR
        force_shimming: Optional[bool] = 'default',
        shimming_solvent_flask: Optional[str] = None,
        shimming_reference_peak: Optional[float] = None,
        **kwargs
    ) -> None:

        # Directly load step properties
        # Similar to a typical super().__init__
        AbstractStep.__init__(self, locals())

        self.validate_props()

    def _prepare_for_analysis(self, graph: 'MultiDiGraph') -> None:
        """Additional preparations for the NMR analysis.

        Executed when `on_prepare_for_execution` is called.

        Checks if shimming is required. Raises an error if required, but no
        suitable solvent found on graph. Issues warning if no shimming will
        be performed.
        """

        shimming_solvent_flask, reference_peak = \
            find_shimming_solvent_flask(graph)

        # Light check
        try:
            assert shimming_solvent_flask
        except AssertionError:
            warning = ShimmingRequired('Found no solvents suitable for \
shimming the NMR. If the procedure is longer than 24 hours shimming will be \
required!')
            warnings.warn(warning)

        # Checking for the last shimming
        if not check_last_shimming_results() or self.force_shimming:
            # If shimming is required, but no suitable solvents found
            if shimming_solvent_flask is None:
                raise NoShimmingSolvent('No solvents suitable for shimming \
the NMR found, but shimming is required!')
            # Else force shimming
            self.force_shimming = True

        # If all okay -> setup the step attributes
        self.shimming_solvent_flask = shimming_solvent_flask
        self.shimming_reference_peak = reference_peak

    def get_preparation_steps(self) -> list['Step']:
        """Returns steps executed before the sample is acquired.

        Shimming mainly, if needed.
        """

        return [
            # Inject sample for shimming
            InjectSample(
                sample_vessel=self.shimming_solvent_flask,
                sample_volume=self.sample_volume,
                target_vessel=self.instrument,
                injection_speed=self.INJECTION_SPEED,
                injection_waste=self.injection_waste,
            ),
            # Shim
            ShimNMR(
                nmr=self.instrument,
                reference_peak=self.shimming_reference_peak,
            ),
            # Discard sample
            CMove(
                from_vessel=self.instrument,
                to_vessel=self.injection_waste,
                volume=self.sample_volume * SAMPLE_DISCARD_EXCESS,
                aspiration_speed=self.INJECTION_SPEED,
                repeats=2,
            )
        # Only if shimming is required
        ] if self.force_shimming else []

    def get_analysis_steps(self) -> list['Step']:
        """Returns steps executed to perform the analysis."""
        return [
            RunNMR(
                nmr=self.instrument,
                on_finish=self.on_finish(self.on_finish_arg),
                **self.method_props
            ),
            # Transferring the sample back
            CMove(
                from_vessel=self.instrument,
                to_vessel=self.vessel,
                volume=self.sample_volume * SAMPLE_MOVE_EXCESS,
                repeats=2,
            )
        ]

    def get_postanalysis_steps(self) -> list['Step']:
        """No steps needed after analysis is complete."""
        return []
