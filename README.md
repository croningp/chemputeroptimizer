# ChemputerOptimizer

The repo contains the optimizer package for Chemputer platform to perform interactive chemical reaction optimizations. Checkout [documentation](/docs/README.md) for details about installation, usage and development. Below is a short guide.

## Installation

1. Clone the repo into desired folder.
```bash
git clone https://gitlab.com/croningroup/chemputer/chemputeroptimizer.git chemputeroptimizer

cd chemputeroptimizer
```
2. Install Chemputer requirements if needed ([XDL](https://gitlab.com/croningroup/chemputer/xdl) and [AnalyticalLabware](https://gitlab.com/croningroup/chemputer/analyticallabware)).
```bash
pip install -r requirements.txt
```
3. Install ChemputerOptimizer.
```bash
pip install .
```

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

### Optimizer Client
ChemputerOptimizer now supports interaction with  Summit benchmarking framework (through [SummitServer](https://gitlab.com/croningroup/personal/ail/summitserver)). List of available algorithms is stored in [/client.py](/chemputeroptimizer/utils/client.py). To use them, run SummitServer main loop on chosen host and change the corresponding constants in `client.py`.

## Features

### v0.3.6 alpha0
* Minor code fixes after merging Raman and HPLC branches.
* Added automatic control experiment every N iterations (see #92).
* Saving state of the `OptimizeDynamicStep` to preserve information about control  experiment result.
* Simulation improved by suppressing flasks/wastes checks.

### v0.4.0
* Major release to catch up with xdl/chemputerxdl v1.1.
* Explicit loss functions.
* Integration tests.
* [Documentation](/docs/README.md).

### v0.4.1
* Catch up with xdl/chemputerxdl v1.5.

### v0.4.2
* Fixed incorrect `OptimizeStep` validation.

## Development

Please check the issue list for the relevant things to do.

If you want to add another algorithm for the optimization, please follow the AbstractAlgorithm class documentation. Testing functions for algorithm evaluation can be found in [/simulation](/tests/simulations/).
