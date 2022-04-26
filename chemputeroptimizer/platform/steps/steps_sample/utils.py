"""Collection of utility functions for analysis steps."""

import warnings
import typing
from typing import Optional, Union

from chemputerxdl.constants import CHEMPUTER_FLASK
from chemputerxdl.utils.execution import get_vessel_stirrer

from ....utils.errors import OptimizerError

if typing.TYPE_CHECKING:
    from networkx import MultiDiGraph


# Validation exceptions
class NoDilutionVessel(OptimizerError):
    """Exception for missing dilution vessel."""

class OptimizerWarning(Warning):
    """Generic warning for stuff related to ChemputerOptimizer."""

def validate_dilution_vessel(
    vessels_for_dilution: list[Optional[str]],
) -> str:
    """Validates if dilution vessel is present."""

    if len(vessels_for_dilution) > 1:
        warning = OptimizerWarning("More than one possible flask for dilution \
found on graph. Consider selecting the one in your procedure.")
        warnings.warn(warning)

    elif len(vessels_for_dilution) == 0:
        raise NoDilutionVessel("No dilution vessel found on the graph. Please \
add at least one empty flask with stirrer attached.")

    return vessels_for_dilution[0]

def get_dilution_flask(graph: 'MultiDiGraph') -> Optional[str]:
    """ Get an empty flask with a stirrer attached to it.

        Used to dilute the analyte before injecting into analytical instrument.
    """

    empty_flasks = [
        flask
        for flask, data in graph.nodes(data=True)
        if data['class'] == CHEMPUTER_FLASK and not data['chemical']
    ]

    for flask in empty_flasks:
        # looking for stirrer attached
        found_stirrer = get_vessel_stirrer(graph, flask)

        # if found stirrer, return current flask
        if found_stirrer:
            return flask

    return None

def get_flasks_for_dilution(graph: 'MultiDiGraph') -> Union[str, list]:
    """Get a list of empty flasks with a stirrers.

    Used to locate a flask to dilute the analyte before injecting into
    analytical instrument.
    """

    empty_flasks = [
        flask
        for flask, data in graph.nodes(data=True)
        if data['class'] == CHEMPUTER_FLASK and not data['chemical']
    ]

    empty_flasks_with_stirrers = [
        flask for flask in empty_flasks
        if get_vessel_stirrer(graph, flask)
    ]

    return empty_flasks_with_stirrers
