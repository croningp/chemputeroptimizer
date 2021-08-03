"""
Module for processing, analysis and comparison of several spectra.
"""
import logging
import json
from typing import List, Optional

import numpy as np

# AnalyticalLabware spectrum classes
from AnalyticalLabware.devices import (
    # RamanSpectrum,
    SpinsolveNMRSpectrum,
    AgilentHPLCChromatogram
)
from AnalyticalLabware.analysis.utils import find_nearest_value_index

from .processing_constants import (
    DEFAULT_NMR_REGIONS_DETECTION,
    TARGET_THRESHOLD_DISTANCE,
    NOVELTY_REGIONS_ANALYSIS,
)
from .novelty_search import (
    expand_peak_regions,
    calculate_information_score,
    calculate_novelty_coefficient,
)

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

    print('Other methods are not supported')
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
        print('Other methods are not supported')
        return regions[-1]

    diff_map = np.abs(regions_ - point)
    if not (diff_map < threshold).any():
        return np.array([])
    return regions[np.argmin(diff_map)]

class SpectraAnalyzer():
    """General class for analyzing spectra differences.

    Class provides methods to compare several spectra, classify the peaks
    according to their changes in time (e.g. starting material, intermediate,
    product or noise) and give the relative information on yield and purity,
    when reference information is supplied.

    Attributes:
        data_path (Optional, str): Valid path to load spectra from.
        reference (Optional, float): Spectrum reference for the current set of
            experiments.
    """
    def __init__(
        self,
        data_path: Optional[str] = None,
        reference: Optional[float] = None,
    ) -> None:

        self.data_path = data_path
        self.logger = logging.getLogger('optimizer.spectraanalyzer')

        # Storing spectral data
        self.spectra = []

        # "Train" regions are used to evaluate the novelty score
        # Include old "known" spectra and those recorded
        # During the current experiment
        self.train_regions: List[np.ndarray] = []

        # Future arguments for peaks classification
        self.starting_material = None
        self.intermediate = None
        self.final_product = None
        self.reference = reference

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
            # Mainly simulation processing
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
            elif 'novelty' in target_parameter:
                # Counting peaks, giving full area not to update
                # Peaks properties of the spectrum
                peaks = self.spectra[-1].find_peaks(
                    area=(self.spectra[-1].x.min(), self.spectra[-1].x.max())
                )
                # n_peaks x 5 matrix of found peaks, see corresponding method
                # In AnalyticalLabware Spectrum class
                return {target_parameter: peaks.shape[0]}

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
        spec.save_data()

        # referencing spectrum by shifting closest peak to the given
        # reference position
        spec.reference_spectrum(reference, 'closest')

        # Selecting best parameters for a given nuclei
        regions_generation_params = DEFAULT_NMR_REGIONS_DETECTION.get(
            spec.parameters['rxChannel'],
            {} # if current nuclei not registered in defaults
        )
        # generating regions of interest first
        regions = spec.generate_peak_regions(
            **regions_generation_params
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
                        # no matching region
                        self.logger.warning('No matching region for peak %s, \
checking closest', peak_position)
                        # checking for closest region
                        closest_region = find_closest_region(
                            regions=regions,
                            point=peak_index,
                            method='mean',
                            threshold=TARGET_THRESHOLD_DISTANCE
                        )
                        if closest_region.size == 0:
                            # if closest peak still far apart,
                            # i.e. further than the threshold distance
                            self.logger.warning('All regions are to far from \
peak %s, either no product formed or target peak shifted, check manually. \
\n found regions: %s', peak_position, spec.x[regions])
                            result = 0

                        else:
                            # found closest, just integrating it
                            result = spec.integrate_area(
                                spec.x[closest_region]
                            )
                    else:
                        self.logger.warning('More than one region matched the \
target peak, resolving')
                        # resolving between several regions
                        peak_index_region = resolve_point_between_regions(
                            regions=regions,
                            point=peak_index,
                            method='mean',
                        )
                        # integrating the best fit region
                        result = spec.integrate_peak(float(peak_position))

                    return {target_parameter: result/reference_value}

                elif 'integration-area' in target_parameter:
                    # splitting "spectrum_integration-area_lll-rrr"
                    _, _, region = target_parameter.split('_')
                    left_w, right_w = region.split('-')
                    self.logger.debug('Integrating spectra within %.2f;%.2f',
                                      left_w, right_w)
                    result = self.spectra[-1].integrate_area(
                        (float(left_w), float(right_w))
                    )

                    return {target_parameter: result}

            elif 'novelty' in target_parameter:
                # Details in the corresponding note
                novelty = self._nmr_novelty_analysis(spec)
                return {target_parameter: novelty}

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
            elif 'novelty' in objective:
                # TODO add best method for peak searching on the chromotogram
                peaks = spec.find_peaks(
                    area=(spec.x.min(), spec.x.max())
                )
                return {objective: peaks.shape[0]}

    def _nmr_novelty_analysis(self, spec: SpinsolveNMRSpectrum) -> List[float]:
        """Calculates novelty score for the given spectrum and all previously
        recorded spectra.
        """

        self.logger.debug('Looking for novelty in NMR spectrum')

        scores: List[float] = []

        # Now calculate new scores for the previous spectra
        # Iterating over reverse spectra list, so that the one currently
        # Investigated will be first to update the "train" regions
        for spectrum in self.spectra[::-1]:
            # Generating regions according to novelty standard
            regions_generation_params = NOVELTY_REGIONS_ANALYSIS.get(
                spectrum.parameters['rxChannel'],
                {} # if current nuclei not registered in defaults
            )
            # Generating regions of interest
            regions = spectrum.generate_peak_regions(
                **regions_generation_params)

            # Flat array of the areas of found regions
            try:
                areas = spectrum.integrate_regions(regions)
            # If working with "simulated" spectrum
            except NotImplementedError:
                areas = np.array([
                    spectrum.integrate_area(spectrum.x[region])
                    for region in regions
                ])

            # Rounding to neglect small differences in ppm scales
            # Across several spectra
            regions_expanded = expand_peak_regions(regions)
            try:
                regions_expanded_xs = np.around(
                    spectrum.x[regions_expanded], 3)

            except IndexError:
                # Raised if no regions found and regions array is empty
                regions_expanded_xs = np.array([])

            information_score = calculate_information_score(regions, areas)

            # Using previously measured spectra as reference
            novelty_coefficient = calculate_novelty_coefficient(
                regions_expanded_xs, self.train_regions
            )

            if spectrum is spec:
                # Updating known, "train" regions with the current spectrum
                self.train_regions.append(regions_expanded_xs)

            scores.append(information_score * novelty_coefficient)

        # Reverse list so that the current one is the last
        return scores[::-1]

    def load_known_regions(self, regions_fp: str) -> None:
        """Loads known regions from a given json file.

        Args:
            regions_fp (str): Json file with the recorded "known" regions.
        """

        with open(regions_fp) as fobj:
            known_regions = json.load(fobj)
            # Iterating and appending to the known regions list
            for _, region in known_regions.items():
                self.train_regions.append(np.array(region))

    def load_test_spectra(self, spectra_fps: List[str]) -> None:
        """Loads test spectra from a list of files.

        These are spectra, that will be used for the novelty evaluation and
        updated with the new information coming.

        Args:
            spectra_fps (List[str]): List of files to load the spectra from.
        """

        for spec_fp in spectra_fps:
            spec = SpinsolveNMRSpectrum(False)
            spec.load_data(spec_fp)
            spec.reference_spectrum(self.reference, 'closest')
            self.spectra.append(spec)
