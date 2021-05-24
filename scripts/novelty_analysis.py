"""
Scrpits to run the novelty analysis over given spectra.

All functions are written to process 19F NMR with fluorobenzene as reference.
"""

from pathlib import Path
import argparse
import random
import json

# Data io
import pandas as pd

# Calculation
import numpy as np

# Spectra loading/processing
from AnalyticalLabware.devices.Magritek.Spinsolve.spectrum import (
    SpinsolveNMRSpectrum
)

from chemputeroptimizer.utils.novelty_search import (
    expand_peak_regions,
    calculate_information_score,
    calculate_novelty_coefficient,
)

# Constants
# Total count of spectra to use as a random sample for referencing
RANDOM_SAMPLE_SIZE = 7

# Config for peak regions analysis
REGIONS_CONFIG = {
    'magnitude': False,
    'derivative': True,
    'smoothed': False,
    'd_merge': 0.1,
    'd_expand': 0.1
}

# Parsing given arguments
parser = argparse.ArgumentParser(description="Analysing spectra for novelty.")

parser.add_argument(
    '--path',
    help='Path to all spectra grouped by iterations',
    type=str,
)

args = parser.parse_args()

data_path = Path(args.path)

# Building spectra dict
specs = {}

for iteration_folder in (
        folder for folder in data_path.iterdir() if folder.is_dir()):
    for pickle in iteration_folder.glob('*.pickle'):
        spec = SpinsolveNMRSpectrum(False)
        # Loading
        spec.load_data(pickle)
        # Referencing to fluorobenzene (-113.15)
        spec.reference_spectrum(-113.15, 'closest')
        specs[iteration_folder.name] = spec

# Building full peak regions map
peaks_regions_map = []

for spec in specs.values():
    regions = spec.generate_peak_regions(**REGIONS_CONFIG)
    expanded_peak_regions = expand_peak_regions(regions)

    x_regions_map = np.around(spec.x[expanded_peak_regions], 4)
    peaks_regions_map.append(x_regions_map)

random_ids = random.sample(range(len(specs)), RANDOM_SAMPLE_SIZE)

regions_rng_sample = [peaks_regions_map[i] for i in random_ids]

# Building list of "training" spectra
train_spectra = [
    iteration
    for i, iteration in enumerate(specs)
    if i in random_ids
]

# Dataframe placeholder
df = pd.DataFrame(
    columns=[
        'Iteration',
        'N regions',
        'Information score',
        'Novelty coefficient',
        'Final score',
        'Train'
    ]
)

# Building the dataframe
for iteration, spec in specs.items():
    print('Processing', iteration)
    regions = spec.generate_peak_regions(**REGIONS_CONFIG)
    regions_len = len(regions)
    regions_expanded = expand_peak_regions(regions)
    # Rounding to neglect small differences in ppm scale
    regions_expanded_xs = np.around(spec.x[regions_expanded], 4)
    information_score = calculate_information_score(spec, regions)
    novelty_coefficient = calculate_novelty_coefficient(
        regions_expanded_xs, regions_rng_sample
    )
    data = {
        'Iteration': iteration,
        'N regions': regions_len,
        'Information score': information_score,
        'Novelty coefficient': novelty_coefficient,
        'Final score': information_score*novelty_coefficient,
        'Train': iteration in train_spectra,
    }
    df = df.append(data, ignore_index=True)

print(df)

df.to_csv('Results.csv', index=False)

known_regions = {
    iteration: region_map.tolist()
    for i, (iteration, region_map) in enumerate(zip(specs, peaks_regions_map))
    if i in random_ids
}

with open('known_regions.json', 'w') as fobj:
    json.dump(known_regions, fobj)
