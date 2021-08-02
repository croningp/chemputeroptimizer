"""
Scrpits to run the novelty analysis over given spectra.

All functions are written to process 19F NMR with fluorobenzene as reference.
"""

# pylint: skip-file

from pathlib import Path
import argparse
import random
import json
from typing import Dict

# Data io
import pandas as pd

# Calculation
import numpy as np
from scipy.stats import hmean as scipy_stats_hmean

# Plotting
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# Spectra loading/processing
from AnalyticalLabware.devices.Magritek.Spinsolve.spectrum import (
    SpinsolveNMRSpectrum
)

from chemputeroptimizer.utils.novelty_search import (
    expand_peak_regions,
    calculate_information_score,
    calculate_novelty_coefficient,
)
from chemputeroptimizer.utils.processing_constants import (
    NOVELTY_REGIONS_ANALYSIS,
)

# Constants for dict keys
REGIONS_XS = 'regions_xs'
REGIONS_YS = 'regions_ys'
REGIONS = 'regions'
AREAS = 'areas'
AREAS_HMEAN = 'areas_hmean'
REGIONS_SIZES = 'regions_sizes'
REGIONS_SCORES = 'regions_scores'
INFORMATION_SCORE = 'information_score'

# Parsing given arguments
parser = argparse.ArgumentParser(description="Analysing spectra for novelty.")

parser.add_argument(
    '--path',
    help='Path to all spectra grouped by iterations',
    type=str,
)

parser.add_argument(
    '--train_size',
    help='Number of top data points to use for building the train regions',
    type=int,
)

args = parser.parse_args()

data_path = Path(args.path)
train_size = args.train_size

HERE = Path(__file__).parent
FIGURES_PATH = HERE.joinpath('figures')
FIGURES_PATH.mkdir(exist_ok=True)
REGIONS_SCORES_FIGURES_PATH = FIGURES_PATH.joinpath('regions scores')
REGIONS_SCORES_FIGURES_PATH.mkdir(exist_ok=True)
NOVELTY_SCORES_FIGURES_PATH = FIGURES_PATH.joinpath('novelty scores')
NOVELTY_SCORES_FIGURES_PATH.mkdir(exist_ok=True)

# Dataframe placeholder
df = pd.DataFrame(
    columns=[
        'Iteration',
        'N regions',
        'Information score',
        'Novelty coefficient',
        'Final score',
        'Train'
    ],
)

### LOADING SPECTRA ###
specs: Dict[str, SpinsolveNMRSpectrum] = {}

for iteration_folder in (
        folder for folder in data_path.iterdir() if folder.is_dir()):
    for pickle in iteration_folder.glob('*.pickle'):
        spec = SpinsolveNMRSpectrum(False)
        # Loading
        spec.load_data(pickle)
        # Referencing to fluorobenzene (-113.15)
        spec.reference_spectrum(-113.15, 'closest')
        specs[iteration_folder.name] = spec

# Building full peak regions maps
full_data = {spec_name: {} for spec_name in specs}

### INFORMATION SCORES ###
for spec_name, spec in specs.items():

    # Looking for regions
    regions = spec.generate_peak_regions(**NOVELTY_REGIONS_ANALYSIS['19F'])
    expanded_peak_regions = expand_peak_regions(regions)

    # Building regions maps
    x_regions_map = np.around(spec.x[expanded_peak_regions], 3)
    y_regions_map = np.around(spec.y[expanded_peak_regions], 3)
    full_data[spec_name][REGIONS_XS] = x_regions_map.tolist()
    full_data[spec_name][REGIONS_YS] = y_regions_map.real.tolist()
    full_data[spec_name][REGIONS] = regions.tolist()

    # Integrating and analyzing
    areas = spec.integrate_regions(regions)
    full_data[spec_name][AREAS] = areas.tolist()
    areas_hmean = scipy_stats_hmean(areas)
    full_data[spec_name][AREAS_HMEAN] = float(areas_hmean)

    # Calculating scores per region
    regions_sizes = regions[:, 1] - regions[:, 0]
    area_diffs = np.abs(areas - areas_hmean)
    area_diffs[area_diffs == 0] = 10
    region_scores = regions_scores = regions_sizes * 1/np.log10(area_diffs)
    full_data[spec_name][REGIONS_SCORES] = region_scores.tolist()
    information_score = np.sum(region_scores) * len(regions)
    full_data[spec_name][INFORMATION_SCORE] = float(information_score)

    data = {
        'Iteration': spec_name,
        'N regions': len(regions),
        'Information score': information_score,
        'Novelty coefficient': 1,
        'Final score': 1,
        'Train': False,
    }

    df = df.append(data, ignore_index=True)

# Setting index for easier data access
df.set_index('Iteration', inplace=True)
# Creating train sample as top <train_size> records by "Information score"
train_samples = df.sort_values('Information score', ascending=False).iloc[:train_size].index

# Dumping full data
with open('full_data.json', 'w') as fobj:
    json.dump(full_data, fobj)

# Dumping regions from the "train samples"
with open('known_regions.json', 'w') as fobj:
    json.dump({
        sample_name: full_data[sample_name][REGIONS_XS]
        for sample_name in train_samples
    }, fobj)

### NOVELTY SCORE ###
full_regions_map = []

# Building the map of all specs regions
for sample in specs:
    full_regions_map.append(
        np.array(full_data[sample][REGIONS_XS])
    )

for spec_name, spec_data in full_data.items():
    novelty_coef = calculate_novelty_coefficient(
        np.array(spec_data[REGIONS_XS]),
        full_regions_map
    )

    df.loc[spec_name, 'Novelty coefficient'] = novelty_coef
    df.loc[spec_name, 'Train'] = True
    df.loc[spec_name, 'Final score'] = spec_data[INFORMATION_SCORE] * novelty_coef

flatten_xs = []
flatten_ys = []
for sample in train_samples:
    flatten_xs.extend(full_data[sample][REGIONS_XS])
    flatten_ys.extend(full_data[sample][REGIONS_YS])

for spec_name, spec_data in full_data.items():
    novelty_coef = calculate_novelty_coefficient(
        np.array(spec_data[REGIONS_XS]),
        full_regions_map
    )

    if spec_name not in train_samples:
        df.loc[spec_name, 'Novelty coefficient'] = novelty_coef
        df.loc[spec_name, 'Final score'] = spec_data[INFORMATION_SCORE] * novelty_coef

        df.loc[spec_name, 'Train'] = False

# Saving results
df.to_csv(f'result_vs_{train_size}.csv')

### VISUALIZATION ###

# Plotting params
SPEC_PLOT_KWS = {
    'lw': 3,
    'alpha': .7,
    'c': 'xkcd:navy',
    'label': 'Target spectrum',
    'zorder': 3
}
SPEC_REGIONS_KWS = {
    'lw': 2,
    'alpha': .7,
    'c': 'xkcd:tangerine',
    'label': 'Identified regions',
    'zorder': 3
}
KNOWN_REGIONS_KWS = {
    'c': 'xkcd:evergreen',
    's': 5,
    'alpha': .2
}
UNKNOWN_REGIONS_KWS = {
    'c': 'xkcd:neon purple',
    's': 80,
    'label': 'Novel',
    'zorder': 2,
    'marker': 'x',
    'alpha': 1,
}

# Plotting regions analysis
for spec_name, spec in specs.items():
    spec_data = full_data[spec_name]

    fig, ax = plt.subplots(figsize=(20, 12))

    spec_plot = ax.plot(spec.x, spec.y, **SPEC_PLOT_KWS)
    for region in spec_data[REGIONS]:
        ax.plot(spec.x[region[0]:region[1]], spec.y[region[0]:region[1]], **SPEC_REGIONS_KWS)

    novelty_diff = np.setdiff1d(spec_data[REGIONS_XS], flatten_xs)
    _, novel_ids, _ = np.intersect1d(np.around(spec.x, 3), novelty_diff, return_indices=True)
    print(spec_name, len(novel_ids))
    novel = ax.scatter(spec.x[novel_ids], spec.y[novel_ids], **UNKNOWN_REGIONS_KWS)
    known = ax.scatter(flatten_xs, flatten_ys, **KNOWN_REGIONS_KWS)

    ax.set_ylim(ax.get_ylim()[0]*.2, spec.y.max()*1.1)
    # ax.set_xlim(-120, -60)

    ax.invert_xaxis()

    ax.set_title(f'{spec_name} vs {train_size}.png')

    known_legend_scatter = Line2D([0], [0], marker='o', color='w', markerfacecolor='xkcd:evergreen', markersize=10, label='Cumulative regions map')
    regions_legend = Line2D([0], [1], marker=None, color='xkcd:tangerine', label='Identified regions', alpha=.7)
    ax.legend(handles=[spec_plot[0], known_legend_scatter, novel, regions_legend], fontsize=14, fancybox=True, shadow=True)

    bbox_dict = {'boxstyle': 'round', 'alpha': .7, 'facecolor': 'white'}
    ax.text(*(0.5, .9), 'Novelty score:\n{:10.5f}'.format(df.loc[spec_name, 'Novelty coefficient']), transform=ax.transAxes, fontsize=14, fontstretch='normal', fontweight='semibold', bbox=bbox_dict)

    fig.savefig(NOVELTY_SCORES_FIGURES_PATH.joinpath(f'{spec_name} vs {train_size}.png'), dpi=400)

    # break
