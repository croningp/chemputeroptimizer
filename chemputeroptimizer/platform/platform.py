from chemputerxdl import ChemputerPlatform

from .steps import (
    Monitor,
    OptimizeStep,
    OptimizeDynamicStep,
    FinalAnalysis,
    Analyze,
)


class OptimizerPlatform(ChemputerPlatform):
    @property
    def step_library(self):
        step_lib = super().step_library
        step_lib['Monitor'] = Monitor
        step_lib['OptimizeStep'] = OptimizeStep
        step_lib['OptimizeDynamicStep'] = OptimizeDynamicStep
        step_lib['FinalAnalysis'] = FinalAnalysis
        step_lib['Analyze'] = Analyze
        return step_lib
