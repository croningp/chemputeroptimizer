"""
Module for processing, analysis and comparison of several spectra.
"""

# Preserving same function signature
# pylint: disable=unused-argument

import logging
import json
from typing import List, Optional, Dict

import numpy as np

# AnalyticalLabware spectrum classes
from AnalyticalLabware.devices import (
    SpinsolveNMRSpectrum,
)

from .processing_constants import (
    NOVELTY_REGIONS_ANALYSIS,
    DEFAULT_NMR_REFERENCING_METHOD
)
from .novelty_search import (
    expand_peak_regions,
    calculate_information_score,
    calculate_novelty_coefficient,
)
from .loss_functions import (
    LossFunctionsCollection,
    NotImplementedFunctionError,
)


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

        # Loss functions collection
        self.losses = LossFunctionsCollection(self.logger)

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

    def spectra_difference(self, spectrum1, spectrum2):
        """Compares two spectra.

        Args:
            spectrum1, spectrum2 - spectra to calculate the difference.

        Returns:
            (float): An average difference between spectra.
        """

        #TODO: additional logic for spectra comparison
        # For now just take an average difference of the Y axis
        # Assuming its the same
        try:
            return np.abs(np.mean(spectrum1.y - spectrum2.y))

        #FIXME: return something meaningful if there is a data mismatch
        except ValueError:
            return 42

    def final_analysis(
        self,
        reference: Optional[float] = None,
        target: Optional[Dict] = None,
        constraints: Optional[List[str]] = None,
    ):
        """Analyses the spectrum relative to provided reference.

        Returns:
            (Dict): A dictionary containing final analysis data.

        Args:
            reference (Any, optional): A peak position (e.g. x coordinate) of
                the reference substance to compare to.
            target (Any, optional): A peak position of the target compound
                (i.e. product). If not supplied, the target will be selected
                automatically from peak classification.
            constraints (List[str], optional): Simple constraints to calculate
                the final result.

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

        # Stub
        results = {}

        for target_parameter in target:
            # Querying loss function
            loss_function = self.losses[(
                self.spectra[-1].__class__.__name__,
                target_parameter,
            )]

            # Calculating result
            try:
                result = loss_function(  # pylint: disable=not-callable
                    spectrum=self.spectra[-1],
                    target=target_parameter,
                    reference=reference,
                    constraints=constraints
                )
                self.logger.debug('Calculating the objective, using <%s>. \
Result: %.2e', loss_function.__name__, result)
            except NotImplementedFunctionError:
                # If the function is not implemented in the loss functions
                # Collection
                self.logger.debug('Special loss function requested.')
                result = None

            # If result is None (i.e. special function signature needed, see
            # NotImplementedFunctionError in the loss functions module),
            # Check if the corresponding loss function is defined
            # For the SpectraAnalyzer class
            if result is None:
                try:
                    # Forging method name to be spectrumclassname_tagretname
                    loss_function = object.__getattribute__(
                        self,
                        self.spectra[-1].__class__.__name__.lower() + '_' + \
                        '_'.join(target_parameter.split('_')[:-1])
                    )
                    # Calling "special" loss function.
                    # Mind no arguments used.
                    result = loss_function(
                        target=target_parameter,
                        reference=reference,
                        constraints=constraints,
                    )
                    self.logger.debug('Special loss function found: <%s>. \
Result calculated: %s', loss_function.__name__, result)

                except AttributeError:
                    # Last resort, special function is required, but not
                    # Defined
                    self.logger.warning('Special loss function not found!')
                    result = float('nan')

            results[target_parameter] = result

        return results

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

    def _spinsolvenmrspectrum_novelty(
            self,
            target: Optional[str] = None,
            reference: Optional[float] = None,
            constraints: Optional[list[str]] = None,
        ) -> List[float]:
        """Calculates novelty score for the last measured spectrum and all
        previously recorded spectra.
        """

        spec: SpinsolveNMRSpectrum = self.spectra[-1]

        # Just in case, should be already referenced when loading.
        if reference is not None:
            spec.reference_spectrum(reference, DEFAULT_NMR_REFERENCING_METHOD)

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

            # If no regions identified on the spectrum
            # Assume no information there
            if not regions.size > 0:
                scores.append(0.0)
                continue

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

    def _simulatedspinsolvenmrspectrum_novelty(self, *args, **kwargs
        ) -> list[float]:
        """Special method for simulated spectra."""
        return self._spinsolvenmrspectrum_novelty()

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

    def control_analysis(
        self,
        spectrum,
        control_experiment_idx,
    ):
        """Process the spectrum from the control experiment.

        Special case to compare it with one of the previously measured spectrum.

        Args:
            spectrum (:obj:AnalyticalLabware.AbstractSpectrum): Spectrum object,
                contaning methods for performing basic processing and analysis.
            control_experiment_idx (int): Id of the previous experiment to
                compare the control experiment to.
        """

        control_result = self.spectra_difference(
            spectrum1=spectrum,
            # Indexing from last
            spectrum2=self.spectra[-control_experiment_idx]
        )

        self.logger.info('Analyzing control experiment. Result: %.2e',
            control_result)

        # Converting to python float for json serializability
        return float(control_result)
