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

from chemputerxdl.steps.base_step import ChemputerStep
from chemputerxdl.utils.execution import (
    get_nearest_node,
    get_pump_max_volume,
)

from chemputerxdl.steps import (
    Transfer,
    CMove,
)
from chemputerxdl.constants import (
    CHEMPUTER_PUMP,
    CHEMPUTER_WASTE,
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
        injection_waste (str): Name of the vessel to dump sample excess. Unless
            given, excess returns to `sample_vessel`.
        injection_speed (float): Speed of sample injection (in mL/min), aka
            `dispense_speed`. Defaults to 5 mL/min.
        sample_excess_volume (float): Excess volume used to prevent air bubbles
            injected. Defaults to 2 mL, however is reduced, if injection pump
            does not fit `sample_volume` + `sample_excess_volume`.

    Attrs aka INTERNAL_PROPS:
        injection_pump (str): Name of the pump used to inject sample, i.e.
            closest to the target vessel.
    """

    PROP_TYPES = {
        'sample_vessel': str,
        'sample_volume': float,
        'injection_waste': str,
        'priming_volume': float,
        'aspiration_speed': float,
        'move_speed': float,
        'injection_speed': float,
        'aspiration_valve': str,
        'sample_excess_volume': float,
        'injection_pump': str,
        'target_vessel': str,
    }

    INTERNAL_PROPS = [
        'injection_waste',
        'sample_excess_volume',
        'injection_pump',
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
        target_vessel: str,
        injection_waste: Optional[str] = None,
        priming_volume: Optional[float] = 'default',
        aspiration_speed: Optional[float] = 'default',
        move_speed: Optional[float] = 'default',
        injection_speed: Optional[float] = 'default',
        aspiration_valve: Optional[str] = None,
        sample_excess_volume: Optional[float] = 'default',
        injection_pump: Optional[str] = None,

        **kwargs
    ) -> None:
        super().__init__(locals())

    def on_prepare_for_execution(self, graph: 'MultiDiGraph') -> None:
        """Prepares step for execution."""

        # Nearest pump needed to store "buffer" of the sample volume
        self.injection_pump = get_nearest_node(
            graph=graph,
            src=self.target_vessel,
            target_vessel_class=CHEMPUTER_PUMP
        )

        injection_pump_max_volume = get_pump_max_volume(
            graph=graph,
            aspiration_pump=self.injection_pump
        )

        # Reducing if the desired volume exceeds the pump's max volume
        if (
            self.sample_excess_volume + \
                self.sample_volume + \
                    self.priming_volume > injection_pump_max_volume
        ):
            self.sample_excess_volume = \
                injection_pump_max_volume - \
                    self.sample_volume - self.priming_volume

        # Obtaining nearest waste to dispose sample before injection
        self.injection_waste = get_nearest_node(
            graph=graph,
            src=self.target_vessel,
            target_vessel_class=CHEMPUTER_WASTE
        )

    def get_steps(self) -> list['Step']:
        """Steps to withdraw, transfer and inject a sample.
        """

        return [
            # Obtain sample and send it to injection pump
            Transfer(
                from_vessel=self.sample_vessel,
                to_vessel=self.injection_pump,
                volume=self.sample_excess_volume + self.sample_volume,
                aspiration_speed=self.aspiration_speed,
                move_speed=self.move_speed,
                dispense_speed=self.move_speed,
            ),
            # Prime the tubing
            CMove(
                from_vessel=self.injection_pump,
                to_vessel=self.injection_waste,
                volume=self.priming_volume,
                aspiration_speed=self.move_speed,
                move_speed=self.move_speed,
                dispense_speed=self.move_speed,
            ),
            # Injecting the sample
            CMove(
                from_vessel=self.injection_pump,
                to_vessel=self.target_vessel,
                volume=self.sample_volume,
                aspiration_speed=self.injection_speed,
                move_speed=self.injection_speed,
                dispense_speed=self.injection_speed,
            ),
            # Returning the excess back to sample vessel
            CMove(
                from_vessel=self.injection_pump,
                to_vessel=self.sample_vessel,
                volume=self.sample_excess_volume,
                aspiration_speed=self.move_speed,
                move_speed=self.move_speed,
                dispense_speed=self.move_speed,
            )
        ]
