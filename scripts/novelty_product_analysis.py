"""
Scripts to run the analysis of the products obtained after novelty search.

All functions are written to process 19F NMR spectra with fluorobenzene as
reference. Change corresponding constants for a different processing.

Hints:
    - Provided path must contain a "full data*.csv" file with all optimization
        data and "spec file" column with corresponding spectra files.

"""

# pylint: skip-file

### IMPORTS
# stdlib
import argparse
import json
from pathlib import Path
from copy import deepcopy

# Data io
import pandas as pd

# Calculations
import numpy as np

# Plotting
import matplotlib.pyplot as plt

# Misc
from tqdm import tqdm

# Spectra processing
from AnalyticalLabware.devices import SpinsolveNMRSpectrum

### CONSTANTS
# Minimum number of spectra containg a region to include this region into
# Product analysis
MIN_SPECTRA_REGION_COUNT = 2

# Expand area of the region for integration
EXPAND_REGION = 0.0

# Settings for regions generation
DEFAULT_REGIONS_SETTINGS = {
    'magnitude': False,
    'derivative': True,
    'smoothed': False,
    'd_merge': 0.0,
    'd_expand': 0.0,
}

# Default specs column name in the full data.csv
SPECS_COLUMN_NAME = 'spec file'

# Reference on the spectrum, fluorobenzene on 19F by default
REFERENCE_KWARGS = {
    'new_position': -113.15,
    'reference': 'closest'
}

# New configuration file stub
NEW_CONFIG_FILE_STUB = {
    'max_iterations': 5,
    'target': {},
    'algorithm': {
        'name': 'smbo',
        'base_estimator': 'GP',
        'acq_func': 'LCB',
        'acq_func_kwargs': {'kappa': 0.001},
        'random_state': 42
    },
    'reference': -113.15,
    'constraints': [],
    'batch_size': 1
}

# New experiment directory name
NEW_EXPERIMENTS_DIR = 'individual optimizations'

# New configuration file name
NEW_CONFIG_FILE_NAME = 'optimization_config_exploitation_constrained.json'

### CLI ARGUMENTS
# Parsing given arguments
parser = argparse.ArgumentParser(
    description='Analysing products from novelty search')

parser.add_argument(
    '--path',
    help='path to all data after running novelty search',
    type=str
)

parser.add_argument(
    '--plots',
    help='generate plots',
    action='store_true',
)

parser.add_argument(
    '--configs',
    help='generate new config files',
    action='store_true',
)

parser.add_argument(
    '--constrained',
    help='if results should be constrained',
    action='store_true',
)

args = parser.parse_args()

data_path = Path(args.path)
if not data_path.is_dir():
    raise FileNotFoundError(f'Provided path {args.path} does not exist.')

HERE = Path(__file__).parent
FIGURES_PATH = None

if args.plots:
    FIGURES_PATH = data_path.joinpath('Novelty analysis figures')
    FIGURES_PATH.mkdir(exist_ok=True)

### PARSING DATA
# Searching for full data table
specs_found = False
full_data_tables = list(data_path.rglob('full data*.csv'))
if full_data_tables:
    # sorting by creation date
    full_data_tables.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    # picking the latest
    full_data_table = full_data_tables[0]
    # reading table
    df = pd.read_csv(full_data_table)

# Fetching specs files
try:
    specs = df[SPECS_COLUMN_NAME].astype(str)
    specs_found = True
except (KeyError, NameError):
    # except df not created or target column not found
    specs_found = False

# Obtaining all spec files
all_specs_paths = list(data_path.rglob('*.pickle'))

# If no data table was found or data table does not contain spec files column
# Use all .pickle files in the data dir as spec files
if specs_found is False:
    spec_paths = all_specs_paths.copy()
else:
    # Else looking for paths for the corresponding spec files
    ps = [p.stem for p in all_specs_paths]
    spec_paths = [all_specs_paths[ps.index(p)] for p in specs]

### LOADING SPECTRA
print('Loading spectra files.')
specs = {}
for spec_path in tqdm(spec_paths):
    spec = SpinsolveNMRSpectrum(False)
    spec.load_data(spec_path)
    spec.reference_spectrum(**REFERENCE_KWARGS)
    specs[spec_path.stem] = spec

### ANALYZING SPECTRA
# Generating spec regions
print('Generating spectra regions')
specs_regs = {}
for key, spec in tqdm(specs.items()):
    regs = spec.generate_peak_regions(**DEFAULT_REGIONS_SETTINGS)
    regs_x = []
    regs_y = []
    for reg in regs:
        reg_x = np.around(spec.x[reg[0]:reg[1]], 3).tolist()
        reg_y = np.around(spec.y[reg[0]:reg[1]].real, 3).tolist()
        regs_x.append(reg_x)
        regs_y.append(reg_y)
    specs_regs[key] = {'x': regs_x, 'y': regs_y}

if args.plots:
    print('Plotting overall stats')
    fig, ax = plt.subplots(figsize=(20, 12))

    for key, regs in specs_regs.items():
        for xs, ys in zip(regs['x'], regs['y']):
            ax.scatter(xs, np.full_like(xs, int(key)), color='xkcd:grey', alpha=.2)

    ax.invert_xaxis()

    fig.savefig(FIGURES_PATH.joinpath('all novelty regions.svg'))

    plt.close()

# Counting all regions found
all_regs_xs = []
for key, regs in specs_regs.items():
    for xs in regs['x']:
        all_regs_xs.extend(xs)

xs_count = []
for x in set(all_regs_xs):
    xs_count.append((x, all_regs_xs.count(x)))

# Filtering points found only in N spectra
xs_valid = [
    x_count[0] for x_count in xs_count
    if x_count[1] > MIN_SPECTRA_REGION_COUNT
]
xs_valid.sort()
xsv = np.array(xs_valid)

# Breaking all points into regions
true_regions = np.split(xsv, np.argwhere(np.diff(xsv) > np.mean(np.diff(xsv))).flatten() + 1)

### SAVING RESULTS
# Plotting
if args.plots:
    print('Plotting all spectra and regions')
    for key, spec in tqdm(specs.items()):
        fig, ax = plt.subplots(figsize=(16, 10))

        ax.plot(spec.x, spec.y.real)

        for tr in true_regions[::-1]:
            xtr = spec.x[np.where((spec.x > tr[0]) & (spec.x < tr[-1]))]
            ytr = spec.y[np.where((spec.x > tr[0]) & (spec.x < tr[-1]))]
            area = spec.integrate_area((tr[-1], tr[0]))
            # print(tr[-1], tr[0])
            ax.scatter(xtr, ytr.real, label=area)


        ax.invert_xaxis()
        ax.legend()

        fig.savefig(FIGURES_PATH.joinpath(f'{key} common regions.png'), dpi=300)
        fig.savefig(FIGURES_PATH.joinpath(f'{key} common regions.svg'))
        plt.close()

# Grouping results
results = {}

for tr in true_regions[::-1]:
    result_key = f'spectrum_integration-area_{tr[-1]}..{tr[0]}'
    results[result_key] = {}

    for key, spec in specs.items():
        xtr = spec.x[np.where((spec.x > tr[0]) & (spec.x < tr[-1]))]
        ytr = spec.y[np.where((spec.x > tr[0]) & (spec.x < tr[-1]))]
        area = spec.integrate_area((tr[-1], tr[0]))

        results[result_key].update({key: area})

results_df = pd.DataFrame(results)
results_df.index = results_df.index.astype('int64')

# Generating constrained results
if args.constrained:
    results_constrained = {}
    for result_key in results:
        constraints = [key for key in results if key != result_key]
        # Calculate constrained result as the result for current region
        # Divided by the sum of all other regions
        result_constrained = results_df[result_key] / results_df[constraints].sum(axis=1)
        results_constrained[result_key] = result_constrained

    results_constrained_df = pd.DataFrame(results_constrained)

# Saving all results
try:
    dfi = df.set_index(SPECS_COLUMN_NAME, drop=False)
    full_df = pd.concat((dfi, results_df), axis=1)
    full_df.to_csv(data_path.joinpath('all products analysis.csv'), index=False)
except NameError:
    results_df.to_csv(data_path.joinpath('all products analysis.csv'), index=False)

if args.constrained:
    try:
        dfi = df.set_index(SPECS_COLUMN_NAME, drop=False)
        full_df_constrained = pd.concat((dfi, results_constrained_df), axis=1)
        full_df_constrained.to_csv(data_path.joinpath('all products analysis (constrained).csv'), index=False)
    except NameError:
        results_constrained_df.to_csv(data_path.joinpath('all products analysis (constrained).csv'), index=False)

### GENERATING NEW CONFIG FILES
if args.configs:
    new_experiments_folder = data_path.joinpath(NEW_EXPERIMENTS_DIR)
    new_experiments_folder.mkdir(exist_ok=True)

    i = 1
    print('Saving new config files in {}'.format(new_experiments_folder.as_posix()))
    for result_key in tqdm(results):
        experiment_folder = new_experiments_folder.joinpath(f'experiment {i}')
        experiment_folder.mkdir(exist_ok=True)

        optimization_config = deepcopy(NEW_CONFIG_FILE_STUB)

        # Building constraints list
        # All regions except for target
        constraints = [
            key.split('_')[-1] for key in results if key != result_key
        ]

        optimization_config['target'] = {result_key: float('inf')}
        if args.constrained:
            optimization_config['constraints'] = constraints

        with open(experiment_folder.joinpath(NEW_CONFIG_FILE_NAME), 'w') as fobj:
            json.dump(optimization_config, fobj, indent=4)

        # Saving results table
        if args.constrained:
            full_df_constrained[full_df.columns[:11].to_list() + [result_key]].to_csv(experiment_folder.joinpath(f'result_table_constrained.csv'), index=False)
        full_df[full_df.columns[:11].to_list() + [result_key]].to_csv(experiment_folder.joinpath(f'result_table.csv'), index=False)
        i += 1
