import os

from chemputeroptimizer import ChemputerOptimizer
from chempiler import Chempiler
import ChemputerAPI
import AnalyticalLabware


HERE = os.path.abspath(os.path.dirname(__file__))

procedure_file = os.path.join(HERE, 'xdl', 'finalanalysis', 'hplc_stir.xdl')
print(procedure_file)

co = ChemputerOptimizer(
    procedure_file,
    os.path.join(HERE, 'graph', 'graph_hplc.json'),
    interactive=False,
)

c = Chempiler(
    experiment_code='',
    graph_file=os.path.join(HERE, 'graph', 'graph_hplc.json'),
    output_dir='',
    simulation=True,
    device_modules=[ChemputerAPI, AnalyticalLabware]
)

for step in co._xdl_object.steps:
    if step.name == 'FinalAnalysis':
        print('FinalAnalysis steps:\n\t', step.steps)

co.prepare_for_optimization()
co.optimize(c)