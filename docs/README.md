# Home
Sort of project documentation. Will be substituted with Wiki/Sphinx.

# Installation
## Requirements
The Chemputeroptimizer requires the following third-party libraries to operate:
- `numpy` - general Python library for array manipulation.
- `scikit-learn>=0.20,<0.24` - machine learning library in Python.
- `scikit-optimize==0.8.1` - Bayesian optimization library based on `scikit-learn` algorithm implementations.
- `pyDOE2` - library for Design of Experiments in Python.

Since chemputeroptimizer targets ChemPU as its hardware platform and XDL as chemical programming language, the following cronin group libraries are required:
- `ChemputerXDL`
- `XDL`
- `chempiler`
- `AnalyticalLabware`

## Installation
1. Clone the repo into desired folder. Master branch always contains most recent updates, although not extensively tested (so does all versions tagged with *alpha*, e.g. `v0.3.0a0`).

```bash
git clone https://gitlab.com/croningroup/chemputer/chemputeroptimizer.git && cd chemputeroptimizer
```

2. Install Chemputer requirements if needed ([XDL](https://gitlab.com/croningroup/chemputer/xdl), [ChemputerXDL](https://gitlab.com/croningroup/chemputer/chemputerxdl) and [AnalyticalLabware](https://gitlab.com/croningroup/chemputer/analyticallabware)).

```bash
pip install -r requirements.txt
```

3. Install ChemputerOptimizer.

```bash
pip install .
```


# QuickStart
1. To use ChemputerOptimizer prepare a XDL procedure with some steps (which parameters should be tweaked during optimization) wrapped with `OptimizeStep`, e.g.
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
Where `optimize_properties` contains the dictionary of the step's properties to optimize. Only continuous variables are supported, therefore `max_value` and `min_value` must be given.

Additionally, add `FinalAnalysis` step, indicating the analytical method and its parameters used for reaction outcome quantification, e.g.:
```xml
<FinalAnalysis
 vessel="reactor"
 method="NMR"
 sample_volume="2.5"
 method_props="{'protocol': '1D FLUORINE HDEC', 'protocol_options': {'centerFrequency': -85, 'PulselengthScale': 1, 'decouplePower': 0, 'AcquisitionTime': 1.64, 'RepetitionTime': 15, 'PulseAngle': 90, 'Number': 64}}"
 force_shimming="True"
 cleaning_solvent="THF" />
```
In this example the reaction mixture sample (2.5 mL) is transferred to the benchtop NMR to perform 19F analysis and calculate the reaction outcome. For additional parameters of the `FinalAnalysis` step -> [[#Final Analysis|here]].

2. Prepare a configuration file, that specifies optimization objective, algorithm name and additional parameters, reference for the spectral analysis, constraints (see below) and parameters for the control experiment. For example:
```json
{
  "max_iterations": 10,
  "target": {
      "spectrum_peak_area_42": "inf"
  },
  "algorithm": {
      "name": "doe"
  },
  "reference": 43,
  "batch_size": 1,
  "constraints": null,
  "control": {
      "n_runs": 0,
      "every": 5
  }
}
```
Full description of parameters is given [[#Configuration|below]].

3. Import necessary modules and run optimization.
```python
from chemputeroptimizer import ChemputerOptimizer

co = ChemputerOptimizer('xdl.xdl', 'graph.json')
co.prepare_for_optimization('configuration.json')

# ChemPU related
from chemiler import Chempiler
from AnalyticalLabware.devices import chemputer_devices
import ChemputerAPI

c = Chempiler('experiment_name', 'graph.json', 'output_dir', False, device_modules=[ChemputerAPI, chemputer_devices])

# Run optimization
co.optimize(c)
```

### Interactive mode
**Under development**

# Reference
## How does it work???
The optimization workflow is managed using the `OptimizeDynamicStep` (ODS), which inherits from abstract `AbstractDynamicStep` and is responsible for dynamic execution of the children steps. In case of ODS, the children steps are taken from the given XDL procedure (i.e., from the XDL object, generated from that procedure). Each iteration is performed as follows:

#### 1. Preparation
1. New copy of the original XDL object is created.
2. The parameters for the indicated XDL steps (i.e. those, that are tweaked during optimization) are updated according to the algorithm suggestion.
3. In case of parallel optimization, several XDL objects are created with corresponding steps parameters and scheduled for parallel execution. Otherwise, a single procedure is just prepared for execution and stored as ODS attribute (called `working_xdl`).
4. For single batch optimization, additional iterator is created from the list of `working_xdl` steps. This iterator is then used to keep track of steps executed, allowing the procedure to be resumed in case of failure.
5. Callbacks for updating the reaction outcome are added to `FinalAnalysis` step.
6. Special steps (i.e. `ConstrainedStep`, see [[#Constrained Step|below]]) are updated.

#### 2. Execution
Execution is managed by the `on_continue` method, which outputs a list of steps to be executed. In case of parallel execution, this list is just steps from `working_xdl`. For single-batch optimization, each step is queried from the steps iterator.
1. When `FinalAnalysis` is executed, the spectrum is measured and passed to the callback function, where the reaction outcome (e.g., peak integration) is performed.
2. The outcome of each batch of optimization is saved in the corresponding folder, including the state of the optimization, list of all parameters and individual XDL file for that particular batch.
3. When the list of steps to execute is exhausted, the ODS checks for the reagent flasks and wastes volumes, loads the data (parameters and reaction outcome) to the algorithm class and updates the XDL object (see [[#1 Preparation|Preparation]] above).
4. If any termination criteria is met, the optimization stops.
5. If control experiment is required, the parameters for that are taken from any of previously performed experiments and analyzed *[[#Result processing|specially]]*.

#### 3. Data management
Each batch is considered completed, when corresponding `FinalAnalysis` step is performed. Each iteration is considered completed, when no more steps to execute are left.

Upon batch completion the following data is saved: current steps parameters, current XDL procedure, current spectrum.

Upon iteration completion the following data is saved: full table of optimization results, schedule (if running in parallel) and current optimization state.

## Special XDL steps
### Final Analysis
The Analyze or FinalAnalysis step performs the reaction analysis when executed. It contains all necessary parameters to run the analysis via Raman, HPLC or NMR instruments, including reaction sampling, sample treatment (e.g., dilution) and instrument control. During the compilation the step’s attributes are additionally checked for consistency (e.g., “dilution volume” if dilution is required) and necessary callback functions (i.e., to update the optimization state upon iteration completion) are assigned. Should be inserted in the procedure after the reaction is complete. The full list of properties is given below:
1. Step related
`vessel` - name of the vessel to perform the analysis and/or take a sample.
`method` - name of the analytical method.
`sample_volume` - volume of the sample to transfer to to the analytical instrument.
`instrument` - name of the analytical instrument (given internally).
`on_finish` - callback function (assigned during the procedure preparation).
`reference_step` - previous step in the procedure, with its properties. Used for additional sample preparations (e.g. dissolving solid after `Filter` step). *Reserved for future use, (given internally)*.
`method_props` - properties of the analytical instrument, e.g. protocol for the NMR. Given as a JSON_PROP_TYPE and passed to the specific analysis step as is.
`batch_id` - batch id, used for referencing.
2. Method related
`cleaning_solvent` - name of the solvent to clean the instrument. Must be given, but ignored for the Raman and other non-sampling analytical methods.
`cleaning_solvent_vessel` - name of the cleaning solvent vessel (given internally).
`priming_waste` - name of the waste container to dispose sample after priming (given internally).
3. Sample related
`sample_pump` - closest pump to `vessel` (given internally).
`injection_pump` - closest pump to `instrument` (given internally).
`sample_excess_volume` - excess of the sample volume to prime the pump, 2 mL by default. This excess is then returned to the reactor.
`dilution_vessel` - vessel, used for dilution.
`dilution_volume` - volume of the solvent to dilute the sample.
`dilution_solvent` - name of the solvent to dilute the sample.
`dilution_solvent_vessel` - name of the vessel for the solvent to dilute the sample (given internally).
`distribution_valve` - name of the distribution valve to inject sample in HPLC (given internally).
`injection_waste` - name of the waste container to dispose the remaining of the sample after injection (given internally).
4. NMR specific
`force_shimming` - True, if shimming is required by default before each analysis. Otherwise, the shimming will be tracked and performed at least every 24 hours.
`shimming_solvent_flask` - name of the flask for the solvent for the shimming (given internally). The solvent is selected from the list of allowed solvents, if none found - exception is raised during compilation.
`shimming_reference_peak` - position of the peak of the solvent used for shimming (given internally).

### Constrained Step
In some cases, additional constraints beyond upper and lower bounds are imposed on the optimization variables. For example, all factors in mixture experiments must sum up to 100%. The `ConstrainedStep` wraps a child step and adjusts the value of a given parameter as a function of the values of selected `OptimizeStep` steps and the desired target value (Fig. S3). In the given example, the volume of the Add step is calculated as in:
```math
V(target) = V(id1) + V(id2) + V(Add)
```
```xml
<OptimizeStep
  id="1"
  optimize_properties="
    {'volume': {'max_value': 20.0, 'min_value': 10.0}}">
  <Add
    vessel="reactor"
    reagent="cyclohexenone"
    volume="10 mL" />
</OptimizeStep>
<ConstrainedStep
  ids="[1, 2]"
  parameter="volume"
  target="50">
  <Add
    reagent="toluene"
    vessel="reactor"
    volume="99999 mL" />
<ConstrainedStep/>
<OptimizeStep
  id="2"
  optimize_properties="
    {'volume': {'max_value': 20.0, 'min_value': 5.0}}">
  <Add
    vessel="reactor"
    reagent="pyrrolidine"
    volume="10 mL" />
</OptimizeStep>
```


## Configuration
The configuration file contains all necessary information to run the optimization and calculate the reaction outcome in a json format. The description of each parameter is given below,:
- `max_iterations` - maximum number of experiments to perform within optimization run.
- `target` - indicates the calculation for the reaction outcome. Available:
	- `spectrum_peak_area_XXX` - peak at XXX position (x coordinate).
	- `spectrum_integration_area_LLL..RRR` - area under the curve with LLL (left) and RRR (right) limits on x axis.
	- `novelty` - novelty, by default is the number of peaks identified. Special implementation for the NMR spectrum (see [[#Novelty|below]]).
- `algorithm` - indicates the algorithm to be used and its respective attributes.
- `reference` - indicates the peak position of the reference compound (i.e., internal reference for the analysis). Is used to reference the spectrum and calculate the reaction outcome.
- `constraints` - lists regions on the reaction spectrum to consider when calculating the final reaction outcome. In the current implementation, the intermediate result (e.g., area under the curve for the target peak) is divided by the sum of integration areas for all listed regions.
- `batch_size` - number of batches to perform the optimization in parallel.
- `control` - parameters to perform the control experiment: `n_runs` - number of control experiment to perform after every `every` number of iterations.

## Modules
### Algorithms
The AlgorithmAPI class is designed to provide a unified interface to the algorithmic classes and dynamic XDL execution. The class contains methods to parse the reaction parameters into parameter-agnostic data arrays suitable for the numeric optimization algorithms, initialize algorithm classes, query data for the next setup and save the intermediate results.
#### Available algorithms
**1.	Random search**
Random search algorithm relies on the random submodule of the NumPy library.5 The suggestion of this algorithm is a random number array (sampled from a uniform distribution) within the parameters constraints. The following parameters are available to construct the algorithm’s class:
- `random_state` – a seed to initialize low-level random number generator, used to preserve reproducibility across multiple optimization runs.

**2.	Genetic algorithm**
A basic genetic algorithm was written and adopted for the sequential optimization of chemical reactions. It uses truncation selection, single point crossover, and random reset mutation while preserving the best solution (elitism). In case of premature convergence, the population is reinitialized. The key hyperparameters to tune are:
- `pop_size` – Number of individuals in the population.
- `mutation_rate` – Probability (0 to 1) of mutating a gene.

**3.	Sequential model-based optimization (SMBO)**
The algorithm implementation is based on the [scikit-optimize](https://scikit-optimize.github.io/stable/) python library and provides a simple and efficient library to minimize expensive and noisy black-box function. The parameters for the underlying algorithm are listed in the official documentation.

**4.	Design of Experiments**
Several experimental designs are available via a wrapper for [pyDOE2](https://github.com/clicumu/pyDOE2). Available designs include full and fractional factorial designs, Response-surface designs, and randomized designs. The wrapper calls the appropriate pyDOE2 functions to generate the design matrix and maps the levels onto the appropriate parameter values based on the search space bounds. For details, checkout the original documentation for [pyDOE](https://pythonhosted.org/pyDOE/).

**5.	Dummy methods**
The following “dummy” methods are given to the user to run the given reaction iteratively using the respective setup on each iteration:
•	`fromcsv` – the next setup is read from the given csv file.
•	`reproduce` – the next setup is equal to the initial setup from the procedure. Used to check the experimental outcome for reproducibility.

### Analyzer
The `SpectraAnalyzer` (SA) class contains methods to manage the spectra and perform the corresponding analysis for the quantification of the reaction outcome. The class is used inside FA step to load the measured spectrum (`load_spectrum`) and call `final_analysis` to get the iteration result. The latter method is called with *reference*, *target* and *constraints* arguments, obtained from optimization configuration.

Additionally, SA contains method to load previously measured spectra (e.g. for novelty search with NMR feedback), processing control experiment (currently under development).

#### Loss Function Collection
The functions for the analysis are presented in the special class: `LossFunctionCollection` and queried by the name of the spectrum class and name of the optimization objective, e.g.:
```python
>>> lfc = LossFunctionCollection()
>>> loss_function = lfc[('SpinsolveNMRSpectrum', 'spectrum_peak_area_42')]
>>> loss_function
<bound method LossFunctionsCollection._spinsolvenmrspectrum_spectrum_peak_area ...>
```

The functions implemented should follow the naming convention as `_spectrumclassname_ojbective_name` and accept 3 arguments: `reference`, `target` and `constraints`. If loss function for the corresponding spectrum class not found, it falls back to *generic* (`_generic_objectivename`). If loss function for the corresponding objective is not found, it falls back to `generic_loss_function`, which returns `Nan` just to keep optimization going.

If analysis function requires more than just reference, target and constraints (e.g. previously measured spectra, like novelty analysis for NMR), that function should raise `NotImplementedFunctionError` and be implemented in the SA class with corresponding name.

##### Novelty
Generic function for novelty search just counts the number of peaks identified on the spectrum. Special treatment is developed for the NMR spectra, where 1) incoming spectrum is analyzed for "information"; 2) the information score is multiplied by the "novelty coefficient", which is the amount of new (with respect to previously measured spectra) peaks in the incoming spectrum. For the details check the SI for the Optimizer paper.
**TODO**: transfer the novelty description.

## Control experiment
The control experiment is the way to monitor the reproducibility of the automated experiments. It can be run "manually", i.e. executing previously saved XDL procedure and comparing the result and output spectrum manually. However, since `v0.3.6a0` the control experiment can be executed automatically, using `control` parameter in the configuration file. Such experiment will be executed with the same parameters as one of the recently performed (selected randomly) and it's result will be saved in the optimization state as `control_result`. For the moment, special methods to quantify control experiment are given in SA, `control_analysis`, and  in AlgorithmAPI, `validate_control`. The SA method will output an mean difference between two spectra, while validate method is reserved for future use.

### Result processing
**Under development**
The *special* processing of the control experiment result is under development. As of now (`v0.4.1`) the control result is saved as mean of the 2 spectra difference (i.e., from the control and original experiments).

## Optimizer Client
**This section is under development**
The `OptimizerClient` represents the class for communication with the `SummitServer`. The communication is based on the TCP-IP sockets and managed via selectors and socket modules of the python standard library. The communication messages are encoded JSON-like dictionaries containing information about the current procedure, steps and parameters subjected to the optimization and optimization configuration. The class is initialized if the requested algorithm is the one available in the Summit framework and managed via `AlgorithmAPI`.

# HOWTO
## Constrain optimization for purity?
If you know your reaction mixture spectrum, i.e., peaks that belong to your product and potential side products, you can "constrain" your optimization to include purity in the objective calculation. To do so, include `constraints` parameter in the optimization configuration with the least of peaks (for `spectrum_peak_area` objective) or regions (as `XX..YY` for `spectrum_integration_area`) of potential side products. Those peaks/regions will be integrated, summed up and the integration area of the product will be divided by that some. 
**Note**
It is highly recommended to use integration *area* (not *peak*), when constraining optimization for purity, as current peak integration method will integrate *closest* peak to the one listed, even if it is not found.

## Run optimization towards reagent conversion?
By default, the algorithms for optimization are set to guide the optimization towards *maximization* of the objective. If you need to *minimize* your target parameter (e.g., starting material peak), you can prepend the objective name with `neg`, for example `neg_spectrum_peak_area`. The integration result in this case will be negated.

## Integrate new analytical instrument?
If you get a new analytical instrument, e.g. `my_awesome_spectrometer`, you have to add the following classes and methods for it, to be implemented into the ChemputerOptimizer workflow.
1. `MyAwesomeSpectrometer` - will be your main communication class, located in the `AnalyticalLabware.devices.myawesomespectrometermanufacturer.myawesomespectrometer` module. This class doesn't inherit anything by default design, however is required to have a method `get_spectrum`, which may or may not return the spectral data, **but** must save it in the corresponding attribute, i.e., `MyAwesomeSpectrometer.spectrum`.
2. `MyAwesomeSpectrometerSpectrum` - will be your class for manipulating the spectral data from your awesome spectrometer. It inherits from `AbstractSpectrum` and should rewrite custom method to `load_spectrum` and save it in the `x` and `y` attributes as numpy arrays. Inherited processing methods (e.g., `correct_baseline`, `integrate_peak`, etc.) must be supported or rewritten.
3. To be integrated into ChemPU workflow, specific device class, `ChemputerMyAwesomeSpectrometer` should be implemented. It inherits from `ChemputerDevice` to support `capabilities` property (i.e., capabilities for liquid transfer) and should list all necessary attributes in its constructor for graph support.
4. Additionally *simulated* instrument classes should be prepared to allow simulating the optimization and running tests.
5. Next, you have to prepare the XDL step to run your awesome spectrometer, `RunMyAwesomeSpectrometer`. Nothing complicated here, follow general guidelines of XDL steps development, declare necessary arguments and their types and write custom `execute` method to perform the acquisition. Here your `get_spectrum` method will come in handy. Additionally, if `on_finish` callback, if given, should be called with copy of you spectrum. This is required to allow reaction outcome calculation at the end of optimization iteration.
6. Next, you have to integrate `RunMyAwesomeSpectrometer` step into ChemputerOptimizer FA pipeline, adding necessary sample preparations, sampling, cleaning, etc. Just check for existing analytical methods for examples.
7. Last, but not least, if your want some special loss function for your spectral analysis (i.e. you are not happy with generic peak integration with `spectrum_peak_area` objective), you should prepare a method for `LossFunctionCollection` class, following the name convention as `_myawesomespectrometerspectrum_spectrum_peak_area`.
8. Declare your awesome spectrometer in `SUPPORTED_ANALYTICAL_METHODS` and `ANALYTICAL_INSTRUMENTS` in `chemputeroptimizer.constants` module.

That's it! Now your awesome spectrometer can be used as an analytical method to analyze your reaction during `FinalAnalysis` step in the optimization workflow.
 
## Write custom analysis function?
To implement your custom analysis (loss) function, you should prepare the following methods.
1. Generic method for all `AbstractSpectrum` spectra classes as `_generic_my_reaction_analysis` in the `LossFunctionCollection` class. This method should accept the following arguments: *spectrum* - instance of the analyzed spectrum class; *target* - name of the target as `target_name_targetvalue` (if that target implies the value, e.g. peak position for the peak integration target); *reference* - position of the reference (aka internal standard) on the spectrum; *constraints* - list of constraints. The output of your function must be *float* type.
2. If any special processing is required for specific spectrum class, corresponding method should be prepared, as `_spectrumclassname_my_reaction_analysis`. The signature is the same as generic method.
3. If your analysis function needs access to more than just one spectrum, the corresponding method in `LossFunctionCollection` should raise `NotImplementedFunctionError` and a method with *exactly same* name should be implemented in `SpectraAnalyzer` class. However, that method should not take *spectrum* argument, since all spectra are saved in the SA class as `spectraanalyzer.spectra`.
4. Declare your loss function in `chemputeroptimizer.constants` in `TARGET_PARAMETERS` list. 

**Note**
A small note on name convention. If your loss function requires any parameter it should be declared as `my_loss_function_name_mylossfunctionparameter`, since it will be parsed to obtain the corresponding method in the `LossFunctionCollection` class. If, however, your loss function *does not* need any parameters, you can declare it as is (i.e. `my_loss_function_name`) in the `constants` module, however its name should be patched in `chemputeroptimizer.validation` module to append underscore (`_`) to its name for the correct parsing.

# Development guide
## Algorithm
All algorithms in the ChemputerOptimizer framework are managed using `AlgorithmAPI` class. In most of the cases it is just responsible for extracting parameters from the dictionaries to arrays and back, with some additional "magic" for special methods (e.g. for novelty, where *all* previous experiments should be updated, when the new result comes). So, to implement new algorithm, you will need to inherit it from `chemputeroptimizer.algorithms.base_algorithm.AbstractAlgorithm` and implement a single method, `suggest`. This method should accept the following arguments:
- `parameters` - (n x i) size matrix where n is number of experiments and i is number of experimental parameters.
- `results` - (n x j) size matrix where j is the number of target parameters.
- `contraints` - tuple with min/max values for the parameters.
- `n_batches` - number of latest executed experiments (batches). `-1` means, that all data should be taken into account, e.g. loading previous experiments.
- `n_returns` - number of new parameters to return (typically equal to number of batches).

The method should return a numpy array of (`n_returns` by `i`) size with new set(s) of experimental input parameters.

**Note**
The method should run even if called with all arguments as `None`.

## Tests
**This section is under development**
Several tests are *currently* implemented for the ChemputerOptimizer library:
- integration: simply run all possible analytical instruments with all possible algorithms and objectives. This is pretty exhaustive (260+ tests as of `v0.3.6`), so a smaller test is written - `test_at_random.py`, which performs N number of tests with (surprise) random configuration.
- unit: these tests are mainly used to check specific functionality. Prepare and/or run them if you've made very specific changes to the framework.

If you've added new analytical instrument and/or loss function, don't forget to add the corresponding graph/xdl/configuration to the test files directory, so it will be picked up during integration tests.

# Roadmap
## Short-term
- Categorical variables.
- Include algorithm testing into overall test pipeline.
- Export "not-only-optimization-related" XDL steps to ChemputerXDL.
- Retire optimization configuration file in favor of optimization description inside XDL file.
## Long-term
- Using Blueprints inside OptimizeDynamicStep to control procedure parameters update.
- Retire OptimizeDynamicStep - in favor of OptimizerPlatform controlling the execution pipeline.
- Advanced spectra comparison for quantitative control experiment validation.
- Custom algorithm for optimization: batch-constrained Bayesian optimization with GP, RF and Bayesian NN for surrogate modeling.
- Advanced parallelization support.
- Multi-objective optimization.