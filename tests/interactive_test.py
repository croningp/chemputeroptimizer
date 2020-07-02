import os

from chemputeroptimizer import ChemputerOptimizer
from chempiler import Chempiler
import ChemputerAPI
import AnalyticalLabware

HERE = os.path.abspath(os.path.dirname(__file__))

co = ChemputerOptimizer(
    os.path.join(HERE, 'xdl', 'test_simple.xdl'),
    os.path.join(HERE, 'graph', 'graph_simple.json'),
    interactive=True,
)

c = Chempiler(
    experiment_code='',
    graph_file=os.path.join(HERE, 'graph', 'graph_simple.json'),
    output_dir='',
    simulation=True,
    device_modules=[ChemputerAPI, AnalyticalLabware]
)

co.prepare_for_optimization()
co.optimize(c)
