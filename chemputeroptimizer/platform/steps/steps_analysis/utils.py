"""Collection of utility functions for analysis steps."""

from typing import Optional, Union

from ....utils.errors import OptimizerError


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
):
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
