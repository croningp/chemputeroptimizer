import os
import argparse
import sys

from chemputeroptimizer import ChemputerOptimizer
from chempiler import Chempiler
import ChemputerAPI
import AnalyticalLabware


parser = argparse.ArgumentParser()
parser.add_argument('-m', '--method', metavar='METHOD', type=str)
parser.add_argument('-s', '--step', metavar='STEP', type=str)
parser.add_argument('-i', '--interactive', action='store_true')

args = vars(parser.parse_args())

HERE = os.path.abspath(os.path.dirname(__file__))
if args['interactive']:
    procedure_file = os.path.join(HERE, 'xdl', 'test_simple.xdl')
elif args['method'] and args['step']:
    procedure_file = f'{args["method"]}_{args["step"]}.xdl'
    procedure_file = os.path.join(HERE, 'xdl', 'finalanalysis', procedure_file)
    print(procedure_file)
else:
    print('Either enter method *and* step to test or select interactive mode')
    sys.exit()

co = ChemputerOptimizer(
    procedure_file,
    os.path.join(HERE, 'graph', 'graph_simple.json'),
    interactive=args['interactive'],
)

for step in co._xdl_object.steps:
    if step.name == 'FinalAnalysis':
        print('FinalAnalysis steps:\n\t', step.steps)
        for substep in step.steps:
            print('\t', substep.name, '\t', substep.properties)

c = Chempiler(
    experiment_code='',
    graph_file=os.path.join(HERE, 'graph', 'graph_simple.json'),
    output_dir='',
    simulation=True,
    device_modules=[ChemputerAPI, AnalyticalLabware]
)

co.prepare_for_optimization(
    os.path.join(HERE, 'xdl', 'optimizer_config.json')
)
co.optimize(c)
