import os

from chemputeroptimizer import ChemputerOptimizer


HERE = os.path.abspath(os.path.dirname(__file__))

o = ChemputerOptimizer(
    os.path.join(HERE, 'xdl', 'test_interactive_fa.xdl'),
    os.path.join(HERE, 'graph', 'graph_1.json'),
    interactive=True
)

print(o.__dict__)

o.prepare_for_optimization()
print('Otpimization steps: ', o._optimization_steps, '\n')
print('Optimization parameters: ', o.optimizer.parameters, '\n')

o.optimizer.update_steps_parameters({'final_parameter': 0.75})
print(o.optimizer._algorithm, o.optimizer._analyzer)
print('Optimization parameters: ', o.optimizer.parameters, '\n')

x = o.optimizer.working_xdl_copy

x.log_human_readable()

print(o.optimizer.properties)
print(o.optimizer.__dict__)
