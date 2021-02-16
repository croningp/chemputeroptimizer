"""
Module for comparing several spectra.
"""
import logging

from typing import Dict
from collections import deque

import numpy as np

# AnalyticalLabware spectrum classes
from AnalyticalLabware import (
    RamanSpectrum,
    SpinsolveNMRSpectrum,
    AgilentHPLCChromatogram
)
from AnalyticalLabware.analysis.utils import find_nearest_value_index


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

    # subtracting and mapping vs 0
    binary_map = np.array(regions - point < 0)

    # logical xor row-wise
    region_map = np.logical_xor(binary_map[:, 0], binary_map[:, 1])

    # returning the matching arguments
    return np.nonzero(region_map)[0]

class SpectraAnalyzer():
    """General class for analyzing spectra differences.

    Class provides methods to compare several spectra, classify the peaks
    according to their changes in time (e.g. starting material, intermediate,
    product or noise) and give the relative information on yield and purity,
    when reference information is supplied.

    Attributes:
        max_spectra (int): Maximum number of spectra to analyze.
        data_path (str): Valid path to load spectra from.
    """
    def __init__(self, max_spectra=5, data_path=None):

        self.data_path = data_path
        self.logger = logging.getLogger('optimizer.spectraanalyzer')

        # Storing spectral data
        self.spectra = deque(maxlen=max_spectra)

        # Dictionary to store regions of interest from loaded spectra
        self.regions = {}

        # Future arguments for peaks classification
        self.starting_material = None
        self.intermediate = None
        self.final_product = None

    def load_spectrum(self, spectrum):
        """Loads the spectrum and stores it in spectra list.

        Args:
            spectrum (:obj:AnalyticalLabware.AbstractSpectrum): Spectrum object,
                contaning methods for performing basic processing and analysis.
        """

        self.logger.debug('Appending spectrum %r', spectrum)
        self.spectra.append(spectrum)

    def add_spectrum(self, spectrum):
        """Updates the latest spectrum.

        The previously measured spectrum stored in self.last_spectrum.

        Args:
            spectrum (Dict): A dictionary containing spectral data, see example
                in self.load_spectrum.__doc__.
        """

    def spectra_difference(self):
        """Compares two most recent spectra.

        Subtract two spectra and give an average difference based on integration
        of the result.

        Returns:
            (float): An average difference between spectra.
        """

    def final_analysis(self, reference=None, target=None):
        """Analyses the spectrum relative to provided reference.

        Returns:
            (Dict): A dictionary containing final analysis data.

        Args:
            reference (Any, optional): A peak position (e.g. x coordinate) of
                the reference substance to compare to.
            target (Any, optional): A peak position of the target compound
                (i.e. product). If not supplied, the target will be selected
                automatically from peak classification.

        Example:
            - if neither reference nor target are provided will return a
                dictionary with peaks parameters of the final product spectrum

            - if no reference is provided will return dictionary of product
                spectrum parameters (peak area or integration area), obtained
                either internally (from self.final_product) or from target
                attribute

            - if both reference and target attributes are provided will return a
                dictionary of final parameter of a given sample
        """

        # spectra specific analysis
        if isinstance(self.spectra[-1], AgilentHPLCChromatogram):
            return self._hplc_analysis(reference, target)

        if isinstance(self.spectra[-1], SpinsolveNMRSpectrum):
            return self._nmr_analysis(reference, target)

        if reference is not None and \
            'Sim' not in self.spectra[-1].__class__.__name__:
            raise NotImplementedError('Supplying reference is not currently \
supported.')

        for target_parameter in target:
            if 'spectrum' in target_parameter:
                if 'peak-area' in target_parameter:
                    # simple case, searching for peak property on a spectrum
                    _, _, peak_position = target_parameter.split('_')
                    result = self.spectra[-1].integrate_peak(
                        float(peak_position)
                        )

                    return {target_parameter: result}
                if 'integration-area' in target_parameter:
                    # splitting "spectrum_integration-area_lll-rrr"
                    _, _, region = target_parameter.split('_')
                    left_w, right_w = region.split('-')
                    result = self.spectra[-1].integrate_area(
                        (float(left_w), float(right_w))
                    )

                    return {target_parameter: result}

        return {'final_parameter': -1}

    def get_yield(self, params):
        """Calculates yield of the final product.

        Args:
            params (Dict): Final analysis parameter dictionary, contaning
                information to calculate the yield, i.e. sample volume and
                reference concentration.
        """

    def get_purity(self, product=None):
        """Calculates the purity of the final product.

        Args:
            product (Any, optional): An a analytical data for the final product,
                e.g. reference peak or full spectrum. If not supplied, will use
                the spectral data obtained during reaction monitoring and
                classified as product.
        """

    def classify_peaks(self):
        """Classifies peaks according to their changes in time."""

    def _filter_noise(self, threshold=None):
        """Filters the peaks classified as noise.

        Peaks are classified as noise if an average difference in time
        for the peak area is below the supplied threshold.

        Args:
            threshold (float, optional): An arbitrary threshold to classify peak
                as noise. If not supplied, will be chosen as a standard
                deviation for peaks, classified as valid (e.g. product or
                starting material).
        """

    def _get_ascending(self):
        """Classifies peaks with increasing area over time."""

    def _get_descending(self):
        """Classifies peaks with decreasing area over time."""

    def _dump(self):
        """Dumps the first spectrum as csv if maximum number of spectra
            reaches max_spectra."""

    def _nmr_analysis(self, reference, target):
        """ Method for performing analysis on NMR spectra. """

        self.logger.debug('Processing spectrum from NMR')
        # looking only in the most recent uploaded spectrum
        spec = self.spectra[-1]

        # generating regions of interest first, best result achieved when
        # searching in "smoothed" and "derivative" modes
        regions = spec.generate_peak_regions(
            magnitude=True,
            derivative=True,
            smoothed=True,
            d_merge=0.01,
            d_expand=0.0075
        )
        self.logger.debug('Found regions, %s', spec.x[regions])

        # integrating the reference if given
        if reference is not None:
            _, reference_index = find_nearest_value_index(spec.x, reference)

            reference_region_index = find_point_in_regions(regions,
                                                           reference_index)

            if reference_region_index.size == 1:
                reference_region_index = reference_region_index[0]
                self.logger.debug('Reference peak matches one of the regions: \
%s', regions[reference_region_index])
                # integrating
                reference_value = spec.integrate_area(
                    spec.x[regions[reference_region_index]])
            else:
                # 0 or more than 1 regions did match the reference point
                # falling back to integrate peak
                self.logger.debug('No regions matched the reference peak, \
fallback to integrating the peak')
                reference_value = spec.integrate_peak(reference)

            self.logger.debug('Integrated the reference peak at %.2f: %.2f',
                              reference, reference_value)
        else:
            reference_value = 1

        # proceed with the target parameter
        for target_parameter in target:
            if 'spectrum' in target_parameter:
                if 'peak-area' in target_parameter:
                    # simple case, searching for peak property on a spectrum
                    _, _, peak_position = target_parameter.split('_')
                    self.logger.debug('Looking for peak at %s', peak_position)
                    _, peak_index = find_nearest_value_index(spec.x,
                                                          float(peak_position))
                    peak_index_region = find_point_in_regions(regions,
                                                              peak_index)

                    if peak_index_region.size == 1:
                        # match!
                        peak_index_region = peak_index_region[0]
                        self.logger.debug('Found matching region %s for peak \
%s', regions[peak_index_region], peak_position)
                        result = spec.integrate_area(
                            spec.x[regions[peak_index_region]]
                        )
                    elif peak_index_region.size == 0:
                        # no matching region, no peak found
                        self.logger.warning('No matching region for peak %s, \
no product formed or processing error, check manually.', peak_position)
                        result = 0
                    else:
                        self.logger.warning('More than one region matched the \
target peak, check below:\n regions: %s, peak: %s',
                                            peak_index_region,
                                            peak_position)
                        result = spec.integrate_peak(float(peak_position))

                    return {target_parameter: result/reference_value}

                if 'integration-area' in target_parameter:
                    # splitting "spectrum_integration-area_lll-rrr"
                    _, _, region = target_parameter.split('_')
                    left_w, right_w = region.split('-')
                    self.logger.debug('Integrating spectra within %.2f;%.2f',
                                      left_w, right_w)
                    result = self.spectra[-1].integrate_area(
                        (float(left_w), float(right_w))
                    )

                    return {target_parameter: result}

    def _hplc_analysis(self, reference, target):
        """
        Calculates Fitness = AUC_target / AUC_istandard.
        In future, consider minimizing side products.
        """
        self.logger.debug('Processing spectrum from HPLC')
        # looking only in the most recent uploaded spectrum
        spec = self.spectra[-1]

        for objective in target:
            if 'spectrum' in objective:
                if 'peak-area' in objective:
                    _, _, peak_position = objective.split('_')
                    AUC_target = spec.integrate_peak(float(peak_position))
                    AUC_istandard = spec.integrate_peak(float(reference))
                    fitness = AUC_target / AUC_istandard

                    return {objective: fitness}
