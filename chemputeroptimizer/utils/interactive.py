"""Methods for interactive parameter input"""

from ..constants import (DEFAULT_OPTIMIZATION_PARAMETERS, TARGET_PARAMETERS)

def interactive_optimization_config():
    print('Welcome to interactive optimization configuration.')
    default = DEFAULT_OPTIMIZATION_PARAMETERS
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

            default['target'] = {parameter: value}
            continue

        msg = f'\nPlease type value for <{param}> parameter\n'
        msg += f'    Default [{default[param]}]\n\n'

        answer = input(msg)

        if answer:
            default[param] = answer

    return default
