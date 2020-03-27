"""Methods for interactive parameter input"""

from ..constants import (
    DEFAULT_OPTIMIZATION_PARAMETERS,
    TARGET_PARAMETERS,
    SUPPORTED_STEPS_PARAMETERS,
)

def interactive_optimization_config():
    print('Welcome to interactive optimization configuration.')
    default = DEFAULT_OPTIMIZATION_PARAMETERS.copy()
    for param in default:

        if param == 'target':
            msg = f'\nPlease select one of the following target parameters\n'
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

        msg = f'\nPlease type value for <{param}> parameter\n'
        msg += f'    Default [{default[param]}]\n\n'

        answer = input(msg)

        try:
            # for max_iterations and final_parameter
            # TODO choice for algorithm by number
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
