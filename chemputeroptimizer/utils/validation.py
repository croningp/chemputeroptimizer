"""
Module contains functions to validate various settings for the
ChemputerOptimizer configuration.
"""

from logging import Logger
from typing import Union
import warnings

from xdl import XDL

from .errors import OptimizerError, ParameterError
from ..constants import (
    SUPPORTED_STEPS_PARAMETERS,
    DEFAULT_OPTIMIZATION_PARAMETERS,
    NOVELTY,
    TARGET,
)


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

def find_and_validate_optimize_steps(
    procedure: XDL,
    logger: Logger,
) -> dict[str, dict]:
    """Find and validate OptimizeSteps in the procedure.

    Args:
        procedure (XDL): XDL procedure to validate.
        logger (Logger): Logger object, for debugging purposes.

    Returns:
        dict[str, dict]: Nested dictionary with OptimizeSteps names and
            properties.

    Raises:
        OptimizerError: If XDL step used in OptimizeStep is not supported.
        ParameterError: If any of the parameters found in OptimizeStep are not
            supported for its child step.
    """

    optimize_steps: dict[str, dict] = {}

    for step in procedure.steps:
        if step.name == 'OptimizeStep':
            # Validating the OptimizeStep child
            optimized_step = step.children[0].name
            if optimized_step not in SUPPORTED_STEPS_PARAMETERS:
                raise OptimizerError(f'Step {optimized_step} is not \
    supported for optimization')

            # Validating target properties for the child step
            for parameter in step.optimize_properties:
                if parameter not in SUPPORTED_STEPS_PARAMETERS[optimized_step]:
                    raise ParameterError(f'Parameter {parameter} is not \
    supported for step {step}')

            optimize_steps.update(
                {f'{optimized_step}_{step.id}': f'{step.optimize_properties}'}
            )

            logger.debug('Found OptimizeStep for %s.', optimized_step)

    return {}

def validate_optimization_config(
    config: dict[str, Union[str, dict]]) -> None:
    """Validate given optimization config.

    Check if any key is absent in the default config and therefore invalid.

    Args:
        config (dict[str, Union[str, dict]]): Configuration dictionary to
            validate.

    Raises:
        ParameterError: If any parameters in the configuration are not valid.
    """

    for parameter in config:
        if parameter not in DEFAULT_OPTIMIZATION_PARAMETERS:
            raise ParameterError(
                f'<{parameter}> not a valid optimization parameter!')

    # Patching target name
    for target_name in config[TARGET]:
        if 'spectrum_peak-area_' in target_name:
            warnings.warn('"spectrum_peak-area_XXX" is obsolete objective \
name, use "spectrum_peak_area_XXX" instead.', category=FutureWarning)
            *_, peak_position = target_name.split('_')
            new_target_name = f'spectrum_peak_area_{peak_position}'
            config[TARGET] = {
                new_target_name: config[TARGET][target_name]
            }

        if 'spectrum_integration-area_' in target_name:
            warnings.warn('"spectrum_integration-area_" is obsolete objective \
name, use "spectrum_integration_area_" instead.', category=FutureWarning)
            *_, area = target_name.split('_')
            new_target_name = f'spectrum_integration_area_{area}'
            config[TARGET] = {
                new_target_name: config[TARGET][target_name]
            }

        if 'novelty' in target_name:
            new_target_name = NOVELTY
            config[TARGET] = {
                new_target_name: config[TARGET][target_name]
            }

def update_configuration(
    config1: dict[str, Union[str, dict]],
    config2: dict[str, Union[str, dict]]
) -> None:
    """Recursively update missing values from two configurations.

    Args:
        config1 (dict): Configuration dictionary to update.
        config2 (dict): Reference configuration dictionary, to pick up missing
            values from.
    """
    for key, value in config2.items():
        if key not in config1:
            config1[key] = value
        elif key == TARGET:
            # Special case - don't update the "target" parameter
            # Otherwise "final_parameter" from default will be appended
            pass
        else:
            if isinstance(value, dict):
                update_configuration(config1[key], value)
