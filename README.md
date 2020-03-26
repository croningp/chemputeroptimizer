# ChemputerOptimizer

The repo contains the optimizer package for Chemputer platoform to perform interactive chemical reaction optimizations.

## Usage

```python
from optimizer import ChemputerOptimizer

co = ChemputerOptimizer('<xdl optimization procedure>', '<optimization graph>', <'path to OptimizeStep steps config'>)
co.prepare_for_optimization(<'path to optimization config'>)
co.optimize('<chempiler instance>')
```

`<xdl optimization procedure>` is any valid `.xdl` procedure with some steps (targeted as optimization parameters) wrapped with *OptimizeStep*, e.g.
```xml
<OptimizeStep
  id="0"
  optimize_properties="{'mass': {'max_value': 0.24, 'min_value': 0.16}}">
  <Add
    reagent="copper(I)iodide"
    vessel="filter"
    mass="0.19 g"
    stir="False" />
</OptimizeStep>
```
Optionally some steps may be wrapped *FinalAnalysis* step with supported analytical method or `interactive` if you want to run optimization loop interactively.
```xml
<FinalAnalysis
  method="method">
  <HeatChill
    vessel="filter"
    temp="25 C"
    time="15 mins" />
</FinalAnalysis>
```
Examples for `.json` config files are available for both [OptimizeStep config](/tests/config/valid_steps.json) and [optimization loop](/tests/config/valid_opt_config.json).

**Note**  
You can omit both OptimizeStep and FinalAnalysis wrappers and run optimization of any procedure interactively by instantiating *ChemputerOptimizer* with `interactive=True` attribute.

## Features

### v0.1.1

* Loading `.json` configuration for optimization and steps to optimize.

* Interactive input for optimization config, optimization steps and FinalAnalysis step.

* No spectral data processing.

## Development

Please check the issue list for the relevant things to do.  
If you want to add another algorithm for the optimization, please follow the AbstractAlgorithm class documentation.
