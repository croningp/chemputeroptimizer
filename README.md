# ChemputerOptimizer

The repo contains the optimizer package to perform interactive chemical reaction optimizations.

## Usage

```python
from optimizer import Optimizer

o = Optimizer('<xdl optimization procedure>')
o.prepare_for_optimization('<optimization graph>')
o.optimize('<chempiler>')
```

## Development

Please check the issue list for the relevant things to do.  
If you want to add another algorithm for the optimization, please follow the AbstractAlgorithm class documentation.
