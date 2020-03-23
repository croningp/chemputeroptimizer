# ChemputerOptimizer

The repo contains the optimizer package to perform interactive chemical reaction optimizations.

## Usage

```python
from optimizer import ChemputerOptimizer

co = ChemputerOptimizer('<xdl optimization procedure>', '<optimization graph>')
co.prepare_for_optimization()
co.optimize('<chempiler>')
```

## Features

### v0.1

* Only random algorithm

* OceanOptics Raman spectrometer for analysis

* No spectral data processing

## Development

Please check the issue list for the relevant things to do.
If you want to add another algorithm for the optimization, please follow the AbstractAlgorithm class documentation.
