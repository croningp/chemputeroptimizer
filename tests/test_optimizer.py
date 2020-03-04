import os

from optimizer import Optimizer

HERE = os.path.abspath(os.path.dirname(__file__))
print(HERE)


o = Optimizer(
    os.path.join(HERE, 'test_optimizer.xdl'),
    os.path.join(HERE, 'graph.json')
)

o.prepare_for_optimization()
