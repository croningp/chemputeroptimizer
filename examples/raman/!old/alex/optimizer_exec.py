import os
from chemputeroptimizer import ChemputerOptimizer
from chempiler import Chempiler
import ChemputerAPI
import AnalyticalLabware.devices

HERE = os.path.abspath(os.path.dirname(__file__))

PROCEDURE = os.path.join(HERE, 'Procedure_attempt_opt.xdl'),
GRAPH = os.path.join(HERE, 'optim_graph.json')

co = ChemputerOptimizer(
    PROCEDURE,
    GRAPH,
    interactive=True,
)

c = Chempiler(
    experiment_code='',
    graph_file=GRAPH,
    output_dir='',
    simulation=True,
    device_modules=[ChemputerAPI, AnalyticalLabware.devices]
)

co.prepare_for_optimization()

co.optimize(c)
