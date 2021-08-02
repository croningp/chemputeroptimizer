"""
Module contains functions to validate various settings for the
ChemputerOptimizer configuration.
"""

from .errors import OptimizerError


def validate_algorithm(algorithm_name: str) -> bool:
    """Raises specific errors when certain algorithms are used.

    Returns True if all okay.
    """

    if algorithm_name == "TSEMO":
        raise NotImplementedError('TSEMO only works with several objectives, \
while ChemputerOptimizer supports only single objective! Consider using "SOBO"\
 or "ENTOMOOT".')

    elif algorithm_name == "MTBO":
        raise NotImplementedError('MTBO currently is not supported! Consider \
using "SOBO" or "ENTMOOT".')

    elif algorithm_name == "NelderMead":
        raise NotImplementedError('NelderMead simplex is not supported! \
Consider using "SNOBFIT"')

    return True

def validate_algorithm_batch_size(
        algorithm_name: str,
        batch_size: int
    ) -> bool:
    """Raises algorithm specific errors.

    Returns True if all okay.
    """

    if algorithm_name == "MTBO" and batch_size > 1:
        raise OptimizerError('MTBO only works for a single batch!')

    elif algorithm_name == "NelderMead" and batch_size > 1:
        raise OptimizerError('NelderMead is not guaranteed to work in batches. \
Consider using a different algorithm.')
