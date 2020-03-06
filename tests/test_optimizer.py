import os

from optimizer import Optimizer

HERE = os.path.abspath(os.path.dirname(__file__))

o = Optimizer(
    os.path.join(HERE, 'test_optimizer.xdl'),
    os.path.join(HERE, 'graph.json')
)

o.prepare_for_optimization()
print('Otpimization steps: ', o._optimization_steps, '\n')
print('Optimization parameters: ', o.optimizer.parameters, '\n')

o.optimizer.get_new_params({'yield': 0.75})
o.optimizer.algorithm.algorithm._parse_data()

print('parameter matrix', o.optimizer.algorithm.algorithm.parameter_matrix, '\n')
print('result matrix', o.optimizer.algorithm.algorithm.result_matrix, '\n')
o.optimizer.get_new_params({'yield': 0.95})
o.optimizer.algorithm.algorithm._parse_data()

print('parameter matrix', o.optimizer.algorithm.algorithm.parameter_matrix, '\n')
print('result matrix', o.optimizer.algorithm.algorithm.result_matrix, '\n')
