import os
import argparse

from chemputeroptimizer import ChemputerOptimizer


parser = argparse.ArgumentParser()
parser.add_argument('-c', '--config', metavar='N', type=int, choices=range(2),
                    help='config number,\n 0 - invalid, 1 - valid')
parser.add_argument('-i', '--interactive', action='store_true')

args = vars(parser.parse_args())
print(args)

HERE = os.path.abspath(os.path.dirname(__file__))
CONFIG_PATH = os.path.join(HERE, 'config')
CONFIGS = [
    'invalid_steps.json',
    'valid_steps.json',
]

if args['config'] is not None:
    config = os.path.join(CONFIG_PATH, CONFIGS[args['config']])
else:
    config = None

o = ChemputerOptimizer(
    os.path.join(HERE, 'xdl', 'test_optimizer_finalanalysis.xdl'),
    os.path.join(HERE, 'graph', 'graph_raman.json'),
    interactive=args['interactive'],
    optimize_steps=config
)

print(o.__dict__)

o.prepare_for_optimization()
print('Otpimization steps: ', o._optimization_steps, '\n')
print('Optimization parameters: ', o.optimizer.parameters, '\n')

o.optimizer.update_steps_parameters({'final_parameter': 0.75})
print(o.optimizer.algorithm_class, o.optimizer._analyzer)
print('Optimization parameters: ', o.optimizer.parameters, '\n')

x = o.optimizer.working_xdl_copy

x.log_human_readable()

print(o.optimizer.properties)
print(o.optimizer.__dict__)
