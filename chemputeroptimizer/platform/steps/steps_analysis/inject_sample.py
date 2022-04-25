"""Special step to withdraw and inject a sample.

Withdraw a sample to "buffer syring", prime excess sample, inject sample,
discard excess.

This step is designed to work correctly with cronin-pumps, where air gap is at
the top of the glass barrel. If other type of syringe pump is used (where
syringe is pointing "top", so air gap is eliminated with liquid movement, i.e.
"TriCont" pump) - this step will guarantee to deliver bubbles into analytical
instrument.
"""

# pylint: disable=unused-argument,attribute-defined-outside-init

import typing
from typing import Optional

from xdl.steps.base_steps import AbstractStep
from xdl.steps.special_steps import Repeat

from chemputerxdl.steps.base_step import ChemputerStep
from chemputerxdl.utils.execution import (
    get_waste_on_valve,
    get_waste_vessel,
    get_aspiration_valve,
)

from chemputerxdl.steps import (
    Transfer,
    Stir,
    CMove,
    Add,
)

from ..utils import (
    get_flasks_for_dilution
)
from .utils import (
    validate_dilution_vessel
)

if typing.TYPE_CHECKING:
    from networkx import MultiDiGraph
    from xdl.steps.base_steps import Step


class InjectSample(ChemputerStep, AbstractStep):
    """XDL step to acquire sample and inject it in another vessel.

    Normally the "vessel" being analytical instrument.

    Args:
        sample_vessel (str): Name of the vessel to withdraw sample from.
        sample_volume (float): Volume of the sample to withdraw.
        target_vessel (str): Name of the vessel where sample is injected.
        priming_volume (float): Volume to prime tubing. Defaults to .5 mL.
        waste_vessel (str): Name of the vessel to dump sample excess. Unless
            given, excess returns to `sample_vessel`.
        injection_speed (float): Speed of sample injection (in mL/min), aka
            `dispense_speed`. Defaults to 5 mL/min.
        sample_excess_volume (float): Excess volume used to prevent air bubbles
            injected. Defaults to 2 mL, however is reduced, if injection pump
            does not fit `sample_volume` + `sample_excess_volume`.

    Attrs aka INTERNAL_PROPS:
        injection_pump (str): Name of the pump, used to inject sample, i.e.
            closest to the target vessel.
    """

    PROP_TYPES = {
        'sample_vessel': str,
        'sample_volume': float,
        'waste_vessel': str,
        'priming_volume': float,
        'aspiration_speed': float,
        'move_speed': float,
        'injection_speed': float,
        'aspiration_valve': str,
        'sample_excess_volume': float,
    }

    INTERNAL_PROPS = [
        'dilution_solvent_vessel',
        'waste_vessel',
        'sample_excess_volume',
    ]

    DEFAULT_PROPS = {
        # Decent defaults for 1/16" tubing
        'priming_volume': 0.5,  # mL
        'aspiration_speed': 10,  # mL/min
        'move_speed': 20,  # mL/min,
        'injection_speed': 5,  # mL/min
        'sample_excess_volume': 2,  # mL
    }

    def __init__(
        self,
        sample_vessel: str,
        sample_volume: float,
        waste_vessel: Optional[str] = None,
        priming_volume: Optional[float] = 'default',
        aspiration_speed: Optional[float] = 'default',
        move_speed: Optional[float] = 'default',
        injection_speed: Optional[float] = 'default',
        aspiration_valve: Optional[str] = None,
        sample_excess_volume: Optional[float] = 'default',

        **kwargs
    ) -> None:
        super().__init__(locals())

    def on_prepare_for_execution(self, graph: 'MultiDiGraph') -> None:
        """Prepares step for execution."""

        if self.waste_vessel is None:
            # Normally return the excess back to the sample vessel
            self.waste_vessel = self.sample_vessel

        # Reduce excess volume if needed

    def get_steps(self) -> list['Step']:
        """Steps to withdraw, transfer and dilute sample.

        Substeps basically mimic the Add step with "reagent" being "reaction
        mixture".
        """

        substeps = []

        return substeps
