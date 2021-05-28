# ChemputerOptimizer

The repo contains the optimizer package for Chemputer platform to perform interactive chemical reaction optimizations.

## Usage

```python
from optimizer import ChemputerOptimizer

co = ChemputerOptimizer('<xdl optimization procedure>', '<optimization graph>')
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

**Note**
You can omit both OptimizeStep and FinalAnalysis wrappers and run optimization of any procedure interactively by instantiating *ChemputerOptimizer* with `interactive=True` attribute.

### Optimizer Client
ChemputerOptimizer now supports interaction with  Summit benchmarking framework (through [SummitServer](https://gitlab.com/croningroup/personal/ail/summitserver)). List of available algorithms is stored in [/client.py](/chemputeroptimizer/utils/client.py). To use them, run SummitServer main loop on chosen host and change the corresponding constants in `client.py`.

## Features

### v0.2.4

* Bugfixes

### v0.2.5 aplha0

* Introduced a [novelty search](chemputeroptimizer\utils\novelty_search.md) as an optimization target.
* Batch-wise parallelization introduced using chemputerxdl scheduling algorithm. Just set the `batch_size` > 1 in the optimization config and ensure enough hardware resources available on your graph. Few limitations:
  * There are no checks for the hardware consistency vs batch size.
  * Parallel execution is only achieved batch-wise, so the time of an iteration is limited to the longest procedure in the current batch.
  * Ideally number of iterations should be proportional to the batch size, otherwise optimization will run `batch size` procedure unless batch * batch size is smaller than `n iterations`.
  * Not yet physically tested, might be buggy!
  * Summit server algorithms not yet supported!

## Development

Please check the issue list for the relevant things to do.
If you want to add another algorithm for the optimization, please follow the AbstractAlgorithm class documentation. Testing functions for algorithm evaluation can be found in [/simulation](/tests/simulations/).
