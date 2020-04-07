import os

from chemputeroptimizer import ChemputerOptimizer

HERE = os.path.abspath(os.path.dirname(__file__))

o = ChemputerOptimizer(
    os.path.join(HERE, 'xdl', 'test_optimizer_finalanalysis.xdl'),
    os.path.join(HERE, 'graph', 'graph_raman.json'),
)

o.prepare_for_optimization()
print('Otpimization steps: ', o._optimization_steps, '\n')
print('Optimization parameters: ', o.optimizer.parameters, '\n')

o.optimizer.update_steps_parameters({'final_yield': 0.75})
print('Optimization parameters*: ', o.optimizer.parameters, '\n')

x = o.optimizer.working_xdl_copy

x.log_human_readable()

print('_______')

while o.logger.handlers:
    o.logger.removeHandler(o.logger.handlers[0])

o = ChemputerOptimizer(
    os.path.join(HERE, 'xdl', 'test_optimizer_finalanalysis.xdl'),
    os.path.join(HERE, 'graph', 'graph_raman.json'),
)

o.prepare_for_optimization()
print('Otpimization steps: ', o._optimization_steps, '\n')
print('Optimization parameters: ', o.optimizer.parameters, '\n')
print(o.optimizer.algorithm_class, o.optimizer._analyzer)

o.optimizer.update_steps_parameters({'final_yield': 0.75})
print(o.optimizer.algorithm_class, o.optimizer._analyzer)
print('Optimization parameters: ', o.optimizer.parameters, '\n')

x = o.optimizer.working_xdl_copy

x.log_human_readable()

print(o.optimizer.properties)
