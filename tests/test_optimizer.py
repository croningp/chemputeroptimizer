import os

from optimizer import Optimizer

HERE = os.path.abspath(os.path.dirname(__file__))

o = Optimizer(
    os.path.join(HERE, './/xdl//test_optimizer.xdl'),
    os.path.join(HERE, './/graph//graph_1.json')
)

o.prepare_for_optimization()
print('Optimization steps: ', o._optimization_steps, '\n')
print('Optimization parameters: ', o.optimizer.parameters, '\n')

o.optimizer.update_steps_parameters({'final_yield': 0.75})
