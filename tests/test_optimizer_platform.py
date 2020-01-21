import os
from xdl import XDL
from optimizer.platform import OptimizerPlatform

HERE = os.path.abspath(os.path.dirname(__file__))
print(HERE)

x = XDL(
    os.path.join(HERE, 'test_optimizer_platform.xdl'),
    platform=OptimizerPlatform
)

for step in x.steps:
    print(step.name, step.properties, '\n')

#graph = x.graph()
x.prepare_for_execution('graph_1.json')

x.log_human_readable()