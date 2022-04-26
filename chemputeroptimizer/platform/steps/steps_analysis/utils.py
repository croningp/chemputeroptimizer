"""Collection of utility functions for analysis steps."""

import typing
from typing import Optional, Union
import warnings

from ....utils.errors import OptimizerError
from ....constants import ANALYTICAL_INSTRUMENTS

if typing.TYPE_CHECKING:
    from networkx import MultiDiGraph

# Validation exceptions
class NoDilutionSolvent(OptimizerError):
    """Exception for missing dilution solvent."""

class MinDilutionRequired(OptimizerError):
    """Exception for insufficient dilution volume defined."""

class NoCleaningSolvent(OptimizerError):
    """Exception for missing cleaning solvent."""

# Validation utility functions
def validate_dilution(
    dilution_volume: Union[float, None],
    dilution_solvent: Union[str, None],
    min_dilution_solvent: Optional[float] = None,
) -> None:
    """Validate dilution properties.

    If dilution volume is given, dilution solvent must be given as well, and
    vice versa.
    """

    if not dilution_solvent and dilution_volume:
        raise NoDilutionSolvent("No dilution solvent is given for a given \
dilution volume.")

    if (min_dilution_solvent is not None and
        dilution_solvent < min_dilution_solvent):
        raise MinDilutionRequired(f"Minimum of {min_dilution_solvent} is \
required for dilution.")

def validate_cleaning(
    sample_volume: Union[float, None],
    dilution_volume: Union[float, None],
    cleaning_solvent: Union[str, None],
) -> None:
    """Validate if cleaning is required and necessary properties given.

    If either sample volume or dilution volume were given -> cleaning solvent
    must be defined to clean either instrument and/or dilution vessel.
    """

    if sample_volume and cleaning_solvent is None:
        raise NoCleaningSolvent("Sample is transferred to the instrument, but \
no cleaning solvent is defined to clean it.")

    if dilution_volume and cleaning_solvent is None:
        raise NoCleaningSolvent("Dilution is performed, but no cleaning \
solvent for dilution vessel is defined.")

def find_instrument(graph: 'MultiDiGraph', method: str) -> Optional[str]:
    """Get the analytical instrument for the given method

    Args:
        method (str): Name of the desired analytical method

    Returns:
        str: ID of the analytical instrument on the supplied graph
    """
    for node, data in graph.nodes(data=True):
        if data['class'] == ANALYTICAL_INSTRUMENTS[method]:
            return node

    return None
