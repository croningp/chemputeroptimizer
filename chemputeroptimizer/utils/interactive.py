"""Methods for interactive parameter input"""

from logging import Logger

from xdl.steps import Step

from .algorithm import ALGORITHMS
from ..platform.steps.optimize_step import OptimizeStep
from ..constants import (
    DEFAULT_OPTIMIZATION_PARAMETERS,
    TARGET_PARAMETERS,
    SUPPORTED_STEPS_PARAMETERS,
    DEFAULT_OPTIMIZE_STEP_PARAMETER_RANGE
)


def interactive_optimization_config():
    print('Welcome to interactive optimization configuration.')
    default = DEFAULT_OPTIMIZATION_PARAMETERS.copy()
    for param in default:

        if param == 'target':
            msg = '\nPlease select one of the following target parameters\n'
            msg += '   '.join(TARGET_PARAMETERS)
            msg += '\n\n'
            parameter = input(msg)

            if not parameter:
                continue

            msg = f'\nPlease type the desired value for the \
{parameter} parameter\n'
            value = input(msg)
            try:
                value = float(value)
            except ValueError:
                print(f'{parameter} value must be float, not {type(value)}')

            default['target'] = {parameter: value}
            continue

        if param == 'algorithm':
            msg = 'Please select on of the following algorithms: \n'
            msg += '    '.join(ALGORITHMS)
            msg += '\n\n'
            algorithm = input(msg)
            while algorithm not in ALGORITHMS:
                print('Wrong algorithm selected, try again!\n')
                algorithm = input()

            algorithm_class = ALGORITHMS[algorithm]
            algorithm_config = algorithm_class.DEFAULT_CONFIG.copy()

            msg = 'Would you like to modify default configuration?\n'
            msg += f'DEFAULT: {algorithm_class.DEFAULT_CONFIG}\n'
            msg += '[n], y: '
            answer = input(msg)

            if answer == 'y':
                for algorithm_param in algorithm_config:
                    msg = f'Please type new value for {algorithm_param} \
parameter or press Enter to skip\n'
                    answer = input(msg)
                    if answer:
                        try:
                            answer = float(answer)
                        except ValueError:
                            pass
                        algorithm_config.update({algorithm_param: answer})

            default['algorithm'].update(name=algorithm, **algorithm_config)
            continue


        msg = f'\nPlease type value for <{param}> parameter\n'
        msg += f'    Default [{default[param]}]\n\n'

        answer = input(msg)

        try:
            # for max_iterations and final_parameter
            answer = float(answer)
        except ValueError:
            pass

        if answer:
            default[param] = answer

    return default

def interactive_optimization_steps(step, step_n):
    msg = f'Found step "{step.name}" at position <{step_n}>,\n'
    msg += 'with following properties: \n'
    msg += f'-----\n{step.properties}\n-----\n'
    msg += 'Would you like to pick it for optimization? '
    msg += '[n], y\n'

    answer = None
    params = {}

    while answer not in ['y', 'n', '']:
        answer = input(msg)
        if not answer or answer == 'n':
            return

        matching_parameters = [
            param
            for param in SUPPORTED_STEPS_PARAMETERS[step.name]
            if step.properties[param] is not None
        ]

        param_msg = f'\n{step.name} step has the following parameters \
for the optimization:\n'
        param_msg += '>>> ' + '  '.join(matching_parameters) + '\n'
        param_msg += '\nPlease type one of them\n'

        param = None
        while param not in ['n', '']:
            param = input(param_msg)
            try:
                print(f'Current value for {param} is {step.properties[param]}')
            except KeyError:
                print(f'"{param}" is not a valid parameter for step {step.name}!')
                continue
            max_value = input(f'Please type maximum value for "{param}": ')
            min_value = input(f'Please type minimum value for "{param}": ')
            try:
                params.update({
                    f'{param}': {'max_value': float(max_value),
                                 'min_value': float(min_value)}})
            except ValueError:
                print('\n!!!Value must be float numbers. Try again!!!')
                continue
            param = input('Any other parameters? ([n], y) ')

    return params

def create_optimize_step(
    step: Step,
    step_id: int,
    params: dict = None,
    logger: Logger = None,
) -> OptimizeStep:
    """Creates an OptimizeStep from supplied xdl step

    Args:
        step (Step): XDL step to be wrapped with OptimizeStep,
            must be supported.
        step_id (int): Ordinal number of a step.
        params (dict, optional): Parameters for the OptimizeStep as
            nested dictionary.

    Example params:
        {'<param>': {'max_value': <value>, 'min_value': <value>}}

    Returns:
        OptimizeStep: An OptimizeStep step wrapped around the XDL step to be
            optimized.
    """

    min_value_range, max_value_range = DEFAULT_OPTIMIZE_STEP_PARAMETER_RANGE

    # If no params given, forge them by default
    if params is None:
        params = {
            param: {
                'max_value': float(step.properties[param]) * max_value_range,
                'min_value': float(step.properties[param]) * min_value_range,
            }
            for param in SUPPORTED_STEPS_PARAMETERS[step.name]
            if step.properties[param] is not None
        }

    # Build an OptimizeStep
    optimize_step = OptimizeStep(
        id=str(step_id),
        children=[step],
        optimize_properties=params,
    )

    logger.debug(
        'Created OptimizeStep for <%s_%d> with following parameters %s',
        step.name, step_id, params)

    return optimize_step
