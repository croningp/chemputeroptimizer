"""
Module for comparing several spectra.
"""
from typing import Dict
from collections import deque

import numpy as np

from AnalyticalLabware.analysis.base_spectrum import AbstractSpectrum


class BaseSpectrum(AbstractSpectrum):
    """Base class to provide methods for spectral processing

    Used in SpectraAnalyzer to obtain spectral properties like peak and
        integration area, also for spectra addition and substraction.
    """

    def __init__(self):
        super().__init__(save_path=False)

    def load_spectrum(self, x, y, timestamp):
        # no special preparations here
        # just redefining abstract method
        super().load_spectrum(x, y, timestamp)

    def save_data(self):
        # don't need to save this
        pass

    def __add__(self, other):
        """Method for addition of several spectra

        Args:
            other (Spectrum object): Instance of
                AnalyticalLabware.AbstractSpectrum.
        """

        raise NotImplementedError

    def __sub__(self, other):
        """Method for subtraction of several spectra

        Args:
            other (Spectrum object): Instance of
                AnalyticalLabware.AbstractSpectrum.

        Returns:
            Tuple[np.array, np.array]: Tuple with X and Y coordinates for
                resulting spectrum.
        """

        try:
            new_x = self.x - other.x
            new_y = self.y - other.y
        except AttributeError:
            raise AttributeError(
                f'Wrong spectrum class supplied ({type(other)}) \
check that "x" attribute for {other} exists.') from None

        except ValueError:
            raise ValueError(f'Spectral data shape mismatch: \
(self - {self.y.shape}, other - {other.y.shape})') from None

        return new_x, new_y


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

        # Storing spectral data
        self.spectra = deque(maxlen=max_spectra)

        # Future arguments for peaks classification
        self.starting_material = None
        self.intermediate = None
        self.final_product = None

    def load_spectrum(self, spectrum):
        """Loads the spectrum and stores it in spectra list.

        Args:
            spectrum (Tuple[np.array, np.array, float]): Tuple with X and Y data
                points for the spectrum and a timestamp.
        """

        spec = BaseSpectrum()
        spec.load_spectrum(*spectrum)
        self.spectra.append(spec)

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
        try:
            _, dif_y = self.spectra[-1] - self.spectra[-2]
        except IndexError:
            raise IndexError('Load at least two spectra.') from None

        return dif_y.mean()

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
        if reference is not None:
            raise NotImplementedError('Supplying reference is not currently \
supported.')

        for target_parameter in target:
            if 'spectrum' in target_parameter:
                if 'peak-area' in target_parameter:
                    # simple case, searching for peak property on a single spectrum
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
