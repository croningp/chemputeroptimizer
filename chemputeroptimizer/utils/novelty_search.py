"""
Module contains function to calculate novelty score. Details are given in the
corresponding notes file.
"""

# for type check
from typing import List
from AnalyticalLabware.devices.Magritek.Spinsolve.spectrum import (
    SpinsolveNMRSpectrum,
)

import numpy as np
from scipy.stats import hmean as scipy_stats_hmean


def expand_peak_regions(peak_regions: np.ndarray) -> np.ndarray:
    """ Helper function to expand the regions into range of points.

    Args:
        peak_regions (np.ndarray): 2D Mx2 array with peak regions indexes (rows)
            as left and right borders (columns).

    Returns:
        np.ndarray: 1D NxK flat array with concatenated regions as point ranges.

    Example:
        >>> expand_peak_regions(np.array([[1, 3], [5, 7]]))
        array([1, 2, 3, 5, 6, 7])
    """

    expanded_regions = []

    for region in peak_regions:
        # include the last point
        expanded_region = range(region[0], region[1]+1)
        expanded_regions.extend(expanded_region)

    return np.array(expanded_regions)

def calculate_information_score(
    spectrum: SpinsolveNMRSpectrum,
    peak_regions: np.ndarray,
) -> float:
    """Calculate information score for the given spectrum.

    Args:
        spectrum (SpinsolveNMRSpectrum): spectrum to calculate the information
            score for.
        peak_regions (np.ndarray): 2D Mx2 array of the indexes of the potential
            peak regions for the given spectrum.

    Returns:
        float: calculated information score.
    """

    # Number of points in each region
    regions_sizes = peak_regions[:, 1] - peak_regions[:, 0]

    # Flat array of the areas of found regions
    areas = spectrum.integrate_regions(peak_regions)

    # Harmonic mean of all areas
    areas_hmean = scipy_stats_hmean(areas)

    # Calculating the score
    area_diffs = np.abs(areas - areas_hmean)
    regions_scores = regions_sizes * 1/np.log10(area_diffs)
    final_score = np.sum(regions_scores) * len(peak_regions)

    return final_score

def calculate_novelty_coefficient(
    spectrum_peaks_region: np.ndarray,
    cumulative_spectra_regions: List[np.ndarray],
) -> float:
    """Calculate novelty coefficient of the given spectrum, based on previous
    spectra.

    Args:
        spectrum_peaks_region (np.ndarray): flatten array of the points (x, ppm)
            of the peak regions from the spectrum of interest.
        cumulative_spectra_regions (List[np.ndarray]): nested list of flatten
            arrays with points (x, ppm) of the peak regions of previous spectra.

    Returns:
        float: calculated novelty coefficient.
    """

    # Flattening all spectra regions
    spectra_regions = []
    for previous_region in cumulative_spectra_regions:
        # Just in case exclude target spectrum if its present
        if np.array_equal(spectrum_peaks_region, previous_region):
            continue
        spectra_regions.extend(previous_region)

    # Calculating the difference
    novelty_diff = np.setdiff1d(spectrum_peaks_region, spectra_regions)

    # Calculating the coefficient
    novelty_coef = len(novelty_diff)/len(spectrum_peaks_region) + \
        1/len(spectra_regions)

    return novelty_coef
