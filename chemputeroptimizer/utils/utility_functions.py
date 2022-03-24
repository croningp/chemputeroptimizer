"""Collection of various utility functions."""

import typing
import warnings

import numpy as np

from AnalyticalLabware.analysis.utils import find_nearest_value_index

from .processing_constants import (
    DEFAULT_NMR_REGIONS_DETECTION,
    DEFAULT_NMR_REFERENCING_METHOD,
)

if typing.TYPE_CHECKING:
    from AnalyticalLabware.devices import SpinsolveNMRSpectrum


### GENERAL
# General utility functions to process spectral data

def find_point_in_regions(regions, point):
    """ Help function to find if the point belong to any given region

    Args:
        regions (:obj:np.array): 2D M x 2 array with peak regions indexes (rows)
            as left and right borders (columns).
        point (int): Point of interest.

    Returns:
        :obj:np.array: Array of indexes for regions where the potential point
            belongs.

    Example:
        >>> regions = np.array([[1, 5], [7, 12]])
        >>> point = 11
        >>> find_point_in_regions(regions, point)
        array([1], dtype=int32)
        # regions[1] -> [7, 12]
    """

    # If 0 regions given, just return empty array
    if not regions.size > 0:
        return np.array([], dtype='int64')

    # subtracting and mapping vs 0
    binary_map = np.array(regions - point < 0)

    # logical xor row-wise
    region_map = np.logical_xor(binary_map[:, 0], binary_map[:, 1])

    # returning the matching arguments
    return np.nonzero(region_map)[0]

def resolve_point_between_regions(regions, point, method='mean'):
    """ Help function to resolve a single point found in several regions.

    The resolving method depends on "method" argument, "mean" - by default -
    computes the mean of each region and returns the one, which mean is closest
    to the point of interest.

    Args:
        regions (:obj:np.array): 2D M x 2 array with peak regions indexes (rows)
            as left and right borders (columns).
        point (int): Point of interest.
        method (str): Method to resolve the regions if the target point is
            found in several regions. "mean" (default) returns the region,
            which mean is closest to the point of interest.

    Returns:
        :obj:np.array: Single region from several regions passed.

    Example:
        >>> regions = np.array([[-113.9, -114.22], [-114.18, -114.48]])
        >>> point = -114.2
        >>> resolve_point_between_regions(regions, point, "mean")
        array([-114.18, -114.48], dtype=float32)
    """

    if method == 'mean':
        # Compute mean along vertical axis
        regions_means = regions.mean(axis=1)
        # Compute absolute differences
        diff_map = np.abs(regions_means - point)
        return regions[np.argmin(diff_map)]

    warnings.warn('Other methods are not supported')
    return regions[-1]

def find_closest_region(regions, point, method='mean', threshold=0.0):
    """ Help function to find a region, closest to the point of interest.

    The resolving method depends on "method" argument, "mean" - by default -
    computes the mean of each region and returns the one, which mean is closest
    to the point of interest.

    Args:
        regions (:obj:np.array): 2D M x 2 array with peak regions indexes (rows)
            as left and right borders (columns).
        point (int): Point of interest.
        method (str): Method to resolve the regions if the target point is nt
            found in any region. "mean" (default) returns the region, which mean
            is closest to the point of interest; "left" will return the region,
            which left border is closest to the point; "right" - for right
            border.
        threshold (float): Maximum distance to consider point *close* to the
            region.

    Returns:
        :obj:np.array: Single region from several regions passed. If the maximum
            distance between closest region and point of interest is greater
            than the threshold - an empty array is returned.

    Example:
        >>> regions = np.array([[-113.9, -114.22], [-114.18, -114.48]])
        >>> point = -114.5
        >>> find_closest_region(regions, point, "mean")
        array([-114.18, -114.48], dtype=float32)
    """

    if method == 'mean':
        # Computing mean
        regions_ = regions.mean(axis=1)
    elif method == 'left':
        # First (left) border for all regions
        regions_ = regions[:, 0]
    elif method == 'right':
        # Second (right) border for all regions
        regions_ = regions[:, 1]
    else:
        warnings.warn('Other methods are not supported')
        return regions[-1]

    diff_map = np.abs(regions_ - point)
    if not (diff_map < threshold).any():
        return np.array([])
    return regions[np.argmin(diff_map)]

def normalize(self, data, peak, mode='height'):
    """Normalizes the spectrum with respect to a peak."""
    if mode == "height":
        #TODO get height for data[peak]
        # return data / height
        pass
    else:
        raise NotImplementedError("Mode not supported.")

### NMR
# NMR spectrum-specific processing functions

def general_nmr_processing(
    spectrum: 'SpinsolveNMRSpectrum',
    reference: float = None,
) -> tuple():
    """General method for processing Spinsolve NMR spectrum.

    Find regions, integrate reference if given.
    """

    # Referencing the spectrum just in case
    if reference is not None:
        spectrum.reference_spectrum(reference, DEFAULT_NMR_REFERENCING_METHOD)

    # Selecting best parameters for a given nuclei
    regions_generation_params = DEFAULT_NMR_REGIONS_DETECTION.get(
        spectrum.parameters['rxChannel'],
        {}  # if current nuclei not registered in defaults
    )
    # Generating regions of interest first
    regions = spectrum.generate_peak_regions(
        **regions_generation_params
    )

    # integrating the reference if given
    if reference is not None:
        _, reference_index = find_nearest_value_index(spectrum.x, reference)

        reference_region_index = find_point_in_regions(regions,
                                                        reference_index)

        if reference_region_index.size == 1:
            reference_region_index = reference_region_index[0]
            # integrating
            reference_value = spectrum.integrate_area(
                spectrum.x[regions[reference_region_index]])
        else:
            # 0 or more than 1 regions did match the reference point
            # falling back to integrate peak
            warnings.warn('No regions matched the reference peak, fallback \
to integrating the peak')
            reference_value = spectrum.integrate_peak(reference)

    else:
        reference_value = 1

    return regions, reference_value
