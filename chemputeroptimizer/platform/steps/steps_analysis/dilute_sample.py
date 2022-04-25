"""Special step to dilute a sample.

Withdraw sample from vessel (with tube priming and flushing), tranfer to
target vessel, add some solvent, stir and wait.
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
    FlushTubing,
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


DEFAULT_PRIME_TIMES = 1

class DiluteSample(ChemputerStep, AbstractStep):
    """XDL step to acquire sample and dilute it in another vessel.

    Args:
        vessel (str): Name of the vessel to withdraw sample from.
        sample_volume (float): Volume of the sample to withdraw.
        dilution_volume (float): Volume of the solvent to dilute with.
        dilution_solvent (str): Solvent to dilute with.
        priming_volume (float): Volume to prime tubing. Defaults to .5 mL.
        dissolution_time (float): Time to stir while diluting. Defaults to 60
            seconds.
        dilution_vessel (str): Name of the vessel where sample is diluted. Must
            have a stirrer attached to it. If none given, searches for the
            first empty flask with stirrer on graph.

    Attrs aka INTERNAL_PROPS:
        dilution_solvent_vessel (str): Name of the dilution solvent vessel on
            the graph.
        waste_vessel (str): Name of the vessel to dump sample while priming.
    """

    PROP_TYPES = {
        'vessel': str,
        'sample_volume': float,
        'dilution_volume': float,
        'dilution_solvent': str,
        'dilution_solvent_vessel': str,
        'waste_vessel': str,
        'priming_volume': float,
        'aspiration_speed': float,
        'move_speed': float,
        'dispense_speed': float,
        'dissolution_time': float,
        'aspiration_valve': str,
        'dilution_vessel': str,
    }

    INTERNAL_PROPS = [
        'dilution_solvent_vessel',
        'waste_vessel',
        'aspiration_valve',
        'dilution_vessel',
    ]

    DEFAULT_PROPS = {
        # Decent defaults for 1/16" tubing
        'priming_volume': 0.5,  # mL
        'aspiration_speed': 10,  # mL/min
        'move_speed': 20,  # mL/min,
        'dispense_speed': 20,  # mL/min
        'dissolution_time': 60,  # mL/min
    }

    def __init__(
        self,
        vessel: str,
        sample_volume: float,
        dilution_volume: float,
        dilution_solvent: str,
        dilution_solvent_vessel: Optional[str] = None,
        waste_vessel: Optional[str] = None,
        priming_volume: Optional[float] = 'default',
        aspiration_speed: Optional[float] = 'default',
        move_speed: Optional[float] = 'default',
        dispense_speed: Optional[float] = 'default',
        dissolution_time: Optional[float] = 'default',
        aspiration_valve: Optional[str] = None,
        dilution_vessel: Optional[str] = None,

        **kwargs
    ) -> None:
        super().__init__(locals())

    def on_prepare_for_execution(self, graph: 'MultiDiGraph') -> None:
        """Prepares step for execution."""

        if self.waste_vessel is None:
            # Obtain the waste vessel closest to reagent
            self.waste_vessel = get_waste_vessel(graph, self.vessel)

        # Obtain the valve through which the reagent is aspired
        self.aspiration_valve = get_aspiration_valve(
            graph, self.vessel, self.waste_vessel
        )

        # Temporary fix. Overwrite waste with backbone waste
        # Use the waste vessel on backbone
        # Important for accuracy in daisy-chained valve setups
        if (
            self.aspiration_valve not in
            list(graph.undirected_neighbors(self.vessel))
        ):
            self.waste_vessel = get_waste_on_valve(
                graph, self.aspiration_valve
            )

        if self.dilution_vessel is None:
            # Get all flasks suitable for dilution
            vessels_for_dilution = get_flasks_for_dilution(graph)

            # TODO replace with sanity check.
            self.dilution_vessel = validate_dilution_vessel(
                vessels_for_dilution)

    def get_steps(self) -> list['Step']:
        """Steps to withdraw, transfer and dilute sample.

        Substeps basically mimic the Add step with "reagent" being "reaction
        mixture".
        """

        substeps = []
        # Prime tubing first
        substeps.extend(self._get_priming_steps())

        substeps.extend([
            # Transferring the target volume
            Transfer(
                from_vessel=self.vessel,
                to_vessel=self.dilution_vessel,
                volume=self.sample_volume,
                aspiration_speed=self.aspiration_speed,
                dispense_speed=self.dispense_speed,
            ),
            # No flushing needed, as dilution solvent will be added next
            Add(
                reagent=self.dilution_solvent,
                vessel=self.dilution_vessel,
                volume=self.dilution_volume,
                stir=True,
                move_speed=self.move_speed,
                aspiration_speed=self.aspiration_speed,
                dispense_speed=self.dispense_speed,
            ),
            # Stir until dissolved
            Stir(
                vessel=self.dilution_vessel,
                time=self.dissolution_time,
                continue_stirring=False,
            )
        ])

        return substeps

    def _get_priming_steps(self) -> list['Step']:
        """Steps to prime tubing before transferring."""

        return [
            Repeat(
                repeats=DEFAULT_PRIME_TIMES,
                children=[
                    CMove(
                        from_vessel=self.vessel,
                        to_vessel=self.waste_vessel,
                        volume=self.priming_volume,
                        move_speed=self.move_speed,
                        aspiration_speed=self.aspiration_speed,
                        dispense_speed=self.dispense_speed,
                    ),
                    FlushTubing(
                        to_vessel=self.waste_vessel,
                        aspiration_valve=self.aspiration_valve,
                    )
                ]
            )
        ]
