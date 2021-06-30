from chemputerxdl import ChemputerPlatform

from .steps import (
    Monitor,
    OptimizeStep,
    OptimizeDynamicStep,
    FinalAnalysis,
    Analyze,
)

from .steps.steps_analysis import RunNMR


class OptimizerPlatform(ChemputerPlatform):
    @property
    def step_library(self):
        step_lib = super().step_library
        step_lib['Monitor'] = Monitor
        step_lib['OptimizeStep'] = OptimizeStep
        step_lib['OptimizeDynamicStep'] = OptimizeDynamicStep
        step_lib['FinalAnalysis'] = FinalAnalysis
        step_lib['Analyze'] = Analyze
        step_lib['RunNMR'] = RunNMR
        return step_lib
