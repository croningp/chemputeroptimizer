# ChemputerOptimizer

The repo contains the optimizer package for Chemputer platform to perform interactive chemical reaction optimizations.

## Installation

1. Clone the repo into desired folder. Versions tagged with *alpha* (e.g. `v0.3.0a0`) are not extensively tested, consider using a stable version (e.g. `v0.2.5`).
```bash
git clone -b v0.2.5 --single--branch https://gitlab.com/croningroup/chemputer/chemputeroptimizer.git chemputeroptimizer

cd chemputeroptimizer
```
2. Install Chemputer requirements if needed ([XDL](https://gitlab.com/croningroup/chemputer/xdl) and [AnalyticalLabware](https://gitlab.com/croningroup/chemputer/analyticallabware)). Mind using legacy version (i.e. `xdl@legacy-0.5.0` and `chemputerxdl@legacy-1.0.0`)
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

**Note**
You can omit both OptimizeStep and FinalAnalysis wrappers and run optimization of any procedure interactively by instantiating *ChemputerOptimizer* with `interactive=True` attribute.

### Optimizer Client
ChemputerOptimizer now supports interaction with  Summit benchmarking framework (through [SummitServer](https://gitlab.com/croningroup/personal/ail/summitserver)). List of available algorithms is stored in [/client.py](/chemputeroptimizer/utils/client.py). To use them, run SummitServer main loop on chosen host and change the corresponding constants in `client.py`.

## Features

### v0.3.3 alpha0

* Novelty search updated and integrated with batch wise operation. See notes in [novelty search](/chemputeroptimizer/utils/novelty_search.md).

### v0.3.4 alpha0
* Fixed `FromCSV` algorithm working in multiple batches (see #85).
* Fixed certain algorithm from reinstantiation during novelty search (see #93).
* Improved data saving (see #80).

### v0.3.5 alpha0
* Added basic constrained optimization (see discussion in #91).
* Improved processing and analysis for the HPLC and Raman feedback.
* Updated script for novel product search.

## Development

Please check the issue list for the relevant things to do.

If you want to add another algorithm for the optimization, please follow the AbstractAlgorithm class documentation. Testing functions for algorithm evaluation can be found in [/simulation](/tests/simulations/).
