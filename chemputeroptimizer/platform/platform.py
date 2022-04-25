"""Optimizer Platform module."""

from chemputerxdl import ChemputerPlatform

from .steps import (
    Monitor,
    OptimizeStep,
    OptimizeDynamicStep,
    FinalAnalysis,
    Analyze,
    StartMonitoring,
    StopMonitoring,
    ConstrainedStep,
    DiluteSample,
)

from .steps.steps_analysis import RunNMR, RunRaman, RunHPLC


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
        step_lib['RunRaman'] = RunRaman
        step_lib['RunHPLC'] = RunHPLC
        step_lib['StartMonitoring'] = StartMonitoring
        step_lib['StopMonitoring'] = StopMonitoring
        step_lib['ConstrainedStep'] = ConstrainedStep
        step_lib['DiluteSample'] = DiluteSample
        return step_lib
