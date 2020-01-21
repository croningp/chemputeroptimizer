from xdl.platforms.chemputer import ChemputerPlatform
from .steps.monitor_steps import Monitor
from .steps.optimize_steps import OptimizeStep, Optimize, FinalAnalysis

class OptimizerPlatform(ChemputerPlatform):

    @property
    def step_library(self):
        step_lib = super().step_library
        step_lib['Monitor'] = Monitor
        step_lib['OptimizeStep'] = OptimizeStep
        step_lib['Optimize'] = Optimize
        step_lib['FinalAnalysis'] = FinalAnalysis
        return step_lib
