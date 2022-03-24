"""Collection of loss functions to run the chemical optimization using XDL.

The collection is represented as a custom mapping class
"LossFunctionCollection" for which custom __getitem__ is written to return the
corresponding loss function.

Not implemented loss functions should be catched during the underlying Analyze
step preparation. If not catched, those functions will return Nan when called
directly from LossFunctionCollection class.

Not implemented analytical instruments should return a generic function defined
for a specific loss. If the latter is not defined OR analytical instrument does
not follow AnalyticalLabware.device.AbstractSpectrum, general function to
handle not implemented arguments will be returned.
"""

# pylint: disable=unused-argument

from typing import (
    Callable,
    Optional,
)
import logging

from AnalyticalLabware.devices import AbstractSpectrum

from .utility_functions import (
    general_nmr_processing,
    find_nearest_value_index,
    find_closest_region,
    find_point_in_regions,
    resolve_point_between_regions,
)
from .processing_constants import (
    TARGET_THRESHOLD_DISTANCE,
)
from ..constants import (
    SUPPORTED_SPECTRA_FOR_ANALYSIS,
)


class NotImplementedFunctionError(NotImplementedError):
    """Generic error for functions not implemented in the collection class.

    Should be used to indicate, that the corresponding function does not follow
    standard loss function signature and should be implemented elsewhere.

    For an example see a novelty search function for the NMR spectrum, which
    accesses all spectra measured so far to calculate novelty coefficient and
    update the corresponding score.
    """

class LossFunctionsCollection():
    """Collection of available loss functions."""

    def __init__(self, logger: logging.Logger = None):
        """Constructor.

        Args:
            logger (logging.Logger): Logger object, mainly for debugging
                purposes. If omitted -> create one with "losslogger" name.
        """
        if logger is not None:
            self.logger = logger
        else:
            self.logger = logging.getLogger('loss_function_logger')

    def __getitem__(
        self,
        loss: tuple[str, str]
    ) -> Callable[['AbstractSpectrum', str, Optional[float], Optional[list[str]]], float]:
        """Returns the requested loss function, based on the name of the
        corresponding spectrum class and loss.

        Args:
            loss(tuple[str, str]): The request loss. First argument is the
                name of the spectrum class, second is the name of the loss.

        Returns:
            Callable: Loss function for a specified spectrum class. Generic
                loss function if spectrum class is not defined.
        """
        # Unpacking tuple
        spec_class, loss_ = loss
        spec_class = spec_class.lower()

        # Stripping of "_Simulated" tag, as most simulated spectrum classes
        # Support default processing methods
        if '_simulated' in spec_class:
            spec_class = spec_class[len('_simulated'):]

        # Checking if spectrum class is supported
        if spec_class not in SUPPORTED_SPECTRA_FOR_ANALYSIS:
            self.logger.warning('Instrument %s is not supported by default, \
fall back to "generic" loss function.', spec_class)
            spec_class = 'generic'

        # Parsing loss name and parameter
        # E.g. loss: "spectrum_peak_area_42" (peak AUC at position 42)
        # Is parsed into "spectrum_peak_area" for loss_name and 42 for param
        *loss_name, _ = loss_.split('_')

        # Returning corresponding loss function
        loss_function = None
        try:
            # If "negative" or "neg" is part of the loss name
            # I.e. the objective has to be negated
            if 'neg' in loss_name or 'negative' in loss_name:
                # Skipping the "negative" tag
                loss_function = object.__getattribute__(
                    self, f'_{spec_class}_' + '_'.join(loss_name[1:])
                )
                # Returning the "negative" loss function
                loss_function = \
                    lambda *args, **kwargs: - loss_function(*args, **kwargs)

            else:
                loss_function = object.__getattribute__(
                    self, f'_{spec_class}_' + '_'.join(loss_name)
                )

        except AttributeError:
            # If no method found, i.e. undefined for the corresponding spectrum
            # Check for a generic loss function for that loss
            loss_function = None
            spec_class = 'generic'

        if loss_function is None:
            try:
                # Checking for the generic loss function
                loss_function = object.__getattribute__(
                    self, f'_{spec_class}_' + '_'.join(loss_name)
                )
                self.logger.warning('No loss function found for %s.', loss[0])
                self.logger.warning('Found generic function for the %s.',
                                    '_'.join(loss_name))
            except AttributeError:
                # Last resort: no loss function is defined
                # For current spectrum class AND loss
                self.logger.warning('No function for %s and %s loss found, \
fall back to generic loss function.', loss[0], loss[1])
                loss_function = self.generic_loss_function

        return loss_function

    def generic_loss_function(
        self,
        spectrum: AbstractSpectrum,
        target: str,
        reference: Optional[float] = None,
        constraints: Optional[list[str]] = None,
    ) -> float:
        """Generic loss function. Accepts required parameters, but always
            returns NaN as a target value.

        Args:
            spectrum (AbstractSpectrum): Spectrum object to perform the
                analysis.
            target (str): Name of the target.
            reference (float): Position of the reference peak on the spectrum.
                Used to find the reference and divide the value of the target
                integration by.
            constraints (list[str]): List of positions or peaks, to divide the
                value of the target by. Typical use case: list of known
                impuruties to minimize.

        Returns:
            float: Calculated value for the specified target.
        """

        # Generic function, always returns NaN
        # Just to keep it the "optimization" going
        return float('nan')

    def _generic_spectrum_peak_area(
        self,
        spectrum: AbstractSpectrum,
        target: str,
        reference: Optional[float] = None,
        constraints: Optional[list[str]] = None,
    ) -> float:
        """Generic loss function for integrating peak on spectrum.

        For argument description see generic_loss_function.
        """
        # Stub
        result = None

        # Processing non-default spectra
        if not isinstance(spectrum, AbstractSpectrum):
            # Just set all values to NaNs
            # For spectra not following AbstractSpectrum class
            result = float('Nan')

        else:
            # Searching for peak property on a spectrum
            *_, peak_position = target.split('_')
            result = spectrum.integrate_peak(float(peak_position))

        # Looking for reference if given
        if reference is not None:
            reference_peak_auc = spectrum.integrate_peak(reference)
            self.logger.info('Calculated reference: %.2e', reference_peak_auc)
        else:
            reference_peak_auc = 1

        # Looking for constraints if given
        if constraints is not None:
            constraints_aucs = []
            for constraint in constraints:
                # Assuming constraint is the list of side product peaks
                # That needs to be integrated and included into the final
                # Target value
                constraint_left, constraint_right = constraint.split('..')
                constraint_auc = spectrum.integrate_area((
                    float(constraint_left), float(constraint_right)
                ))
                constraints_aucs.append(constraint_auc)
            constraints_auc = sum(constraints_aucs)
            self.logger.info('Calculated constraints: %.2e', constraints_auc)

            # FIXME: this is temporary solution, in ideal case
            # Constraints should not increase the result
            # Only reduce it if any constraint found

            # Avoiding zero division
            constraints_auc += 1e-5
        else:
            constraints_auc = 1

        try:
            # Dividing by reference
            result = result / reference_peak_auc
            # Dividing by constraints
            result = result / constraints_auc
        except ZeroDivisionError:
            pass

        return result

    def _generic_spectrum_integration_area(
        self,
        spectrum: AbstractSpectrum,
        target: str,
        reference: Optional[float] = None,
        constraints: Optional[list[str]] = None,
    ) -> float:
        """Generic loss function to calculate integration area on spectrum.

        Same as peak-area, but using definite area limits for integration.

        For argument description see generic_loss_function.
        """
        # Stub
        result = None

        # Processing non-default spectra
        if not isinstance(spectrum, AbstractSpectrum):
            # Just set all values to NaNs
            # For spectra not following AbstractSpectrum class
            result = float('Nan')

        else:
            # Searching for peak property on a spectrum
            *_, area = target.split('_')
            left, right = area.split('..')
            result = spectrum.integrate_area((float(left), float(right)))
            self.logger.info('Integrated area %s-%s: %.2e', left, right, result)

        # Looking for reference if given
        if reference is not None:
            reference_peak_auc = spectrum.integrate_peak(reference)
            self.logger.info('Calculated reference: %.2e', reference_peak_auc)
        else:
            reference_peak_auc = 1

        # Looking for constraints if given
        if constraints is not None:
            constraints_aucs = []
            for constraint in constraints:
                # Assuming constraint is the list of side product peaks
                # That needs to be integrated and included into the final
                # Target value
                constraint_left, constraint_right = constraint.split('..')
                constraint_auc = spectrum.integrate_area((
                    float(constraint_left), float(constraint_right)
                ))
                constraints_aucs.append(constraint_auc)
            constraints_auc = sum(constraints_aucs)
            self.logger.info('Calculated constraints: %.2e', constraints_auc)

            # Avoiding zero division
            constraints_auc += 1e-5
        else:
            constraints_auc = 1

        try:
            # Dividing by reference
            result = result / reference_peak_auc
            # Dividing by constraints
            result = result / constraints_auc
        except ZeroDivisionError:
            pass

        return result

    def _generic_novelty(
        self,
        spectrum: AbstractSpectrum,
        target: str,
        reference: Optional[float] = None,
        constraints: Optional[list[str]] = None,
    ) -> float:
        """Generic function to search for novelty.

        By default just count the number of peaks found.

        For argument description see generic_loss_function.
        """

        # Counting peaks, giving full area
        # So that peaks attribute for the spectrum is not updated
        # See AnalyticalLabware class for description
        peaks = spectrum.find_peaks(
            area=(spectrum.x.min(), spectrum.x.max())
        )

        # Returning number of peaks found
        return peaks.shape[0]

    def _spinsolvenmrspectrum_spectrum_peak_area(
        self,
        spectrum: AbstractSpectrum,
        target: str,
        reference: Optional[float] = None,
        constraints: Optional[list[str]] = None,
    ) -> float:
        """Spinsolve NMR spectrum-specific method to obtain area under the
            curve (AUC) for the given peak.

        The method is based on the regions analysis: the target peak is checked
        vs. identified peak regions. If target peak is not found in any region,
        the result is returned as 0, i.e. no product formed. Regions can
        overlap, in which case the peak found in more than one regions, will
        be resolved between them, according to the distance to mean of those
        regions.

        For argument description see generic_loss_function.
        """

        # Start with general processing to get the regions and reference AUC
        regions, reference_peak_auc = general_nmr_processing(
            spectrum=spectrum, reference=reference
        )
        self.logger.debug('Regions found: %s', spectrum.x[regions])

        # Unpacking peak position
        *_, peak_position = target.split('_')
        self.logger.debug('Looking for peak at %s', peak_position)

        # Looking for exact point on spectrum
        _, peak_index = find_nearest_value_index(spectrum.x,
                                                float(peak_position))
        peak_index_region = find_point_in_regions(regions,
                                                    peak_index)

        if peak_index_region.size == 1:
            # Match! Just integrate the area
            peak_index_region = peak_index_region[0]
            self.logger.debug('Found matching region %s for peak %s',
                              regions[peak_index_region], peak_position)
            result = spectrum.integrate_area(
                spectrum.x[regions[peak_index_region]]
            )

        elif peak_index_region.size == 0:
            # No matching region
            self.logger.warning('No matching region for peak %s, \
checking closest', peak_position)

            # Checking for closest region
            closest_region = find_closest_region(
                regions=regions,
                point=peak_index,
                method='mean',
                threshold=TARGET_THRESHOLD_DISTANCE
            )

            if closest_region.size == 0:
                # No closest regions found, meaning that
                # The closest peak still far apart,
                # I.e. further than the threshold distance
                self.logger.warning('All regions are to far from \
peak %s, either no product formed or target peak shifted, check manually. \
\n found regions: %s', peak_position, spectrum.x[regions])

                # Typically means no product formed
                result = 0

            else:
                # Found closest, just integrating it
                result = spectrum.integrate_area(
                    spectrum.x[closest_region]
                )

        else:
            # If point belongs to more than one region,
            # I.e., located on the intersection of two regions
            self.logger.warning('More than one region matched the \
target peak, resolving')
            # Resolving between several regions
            peak_index_region = resolve_point_between_regions(
                regions=regions,
                point=peak_index,
                method='mean',
            )
            # Integrating the best fit region
            result = spectrum.integrate_peak(float(peak_position))

        # Looking for constraints if given
        # Methods follows generic loss function
        if constraints is not None:
            constraints_aucs = []
            for constraint in constraints:
                # Assuming constraint is the list of side product peaks
                # That needs to be integrated and included into the final
                # Target value
                constraint_left, constraint_right = constraint.split('..')
                constraint_auc = spectrum.integrate_area((
                    float(constraint_left), float(constraint_right)
                ))
                constraints_aucs.append(constraint_auc)
            constraints_auc = sum(constraints_aucs)
            self.logger.info('Calculated constraints: %.2e', constraints_auc)

            # Avoiding zero division
            constraints_auc += 1e-5
        else:
            constraints_auc = 1

        # Dividing
        try:
            # Dividing by reference
            result = result / reference_peak_auc
            # Dividing by constraints
            result = result / constraints_auc
        except ZeroDivisionError:
            pass

        return result

    def _spinsolvenmrspectrum_spectrum_integration_area(
        self,
        spectrum: AbstractSpectrum,
        target: str,
        reference: Optional[float] = None,
        constraints: Optional[list[str]] = None,
    ) -> float:
        """Spinsolve NMR spectrum-specific method to obtain area under the
            curve (AUC) with specified left and right limits.

        For argument description see generic_loss_function.
        """

        # General processing
        general_nmr_processing(spectrum=spectrum, reference=reference)

        # The rest just follows corresponding generic function
        return self._generic_spectrum_integration_area(
            spectrum=spectrum,
            target=target,
            reference=reference,
            constraints=constraints
        )

    def _spinsolvenmrspectrum_novelty(
        self,
        spectrum: AbstractSpectrum,
        target: str,
        reference: Optional[float] = None,
        constraints: Optional[list[str]] = None,
    ) -> float:
        """Spinsolve NMR spectrum-specific method to look for novelty.

        This method requires access to all previous data, so does not fall
        into general collection of loss function.

        For argument description see generic_loss_function.
        """

        raise NotImplementedFunctionError

    def _ramanspectrum_spectrum_peak_area(
        self,
        spectrum: AbstractSpectrum,
        target: str,
        reference: Optional[float] = None,
        constraints: Optional[list[str]] = None,
    ) -> float:
        """Raman spectrum-specific method to integrate peaks.

        For argument description see generic_loss_function.
        """

        # FIXME: this method should be "integrate_area"
        *_, peak_position = target.split('_')
        AUC_target = spectrum.integrate_area(
            (float(peak_position) - 13, float(peak_position) + 17))
        AUC_istandard = spectrum.integrate_area(
            (float(reference) - 18, float(reference) + 17))
        fitness = AUC_target / AUC_istandard

        return fitness

    def _agilenthplcchromatogram_spectrum_peak_area(
        self,
        spectrum: AbstractSpectrum,
        target: str,
        reference: Optional[float] = None,
        constraints: Optional[list[str]] = None,
    ) -> float:
        """Method for integrating peak area, specific for Agilent Chromatogram
            class.

        For argument description see generic_loss_function.
        """

        # FIXME: get rid of hardcoded values
        *_, peak_position = target.split('_')
        AUC_target = spectrum.integrate_peak(float(peak_position))
        is_interval = (float(reference)-0.2, float(reference)+0.2)
        AUC_istandard = spectrum.integrate_area(is_interval)
        fitness = AUC_target / AUC_istandard
        # TODO: implement "constraints" calculation
        # maximizing area & purity

        # # calculate area
        # _, _, peak_position = objective.split('_')
        # AUC_target = spec.integrate_peak(float(peak_position))
        # is_interval = (float(reference)-0.2, float(reference)+0.2)
        # AUC_istandard = spec.integrate_area(is_interval)
        # rel_yield = AUC_target / AUC_istandard

        # #calculate purity
        # # crop IS & convert to seconds
        # fine_spec = copy.deepcopy(spec)
        # fine_spec.trim(5, 18)
        # fine_spec.x = fine_spec.x * 60
        # fine_spec.find_peaks(0.01, 1)
        # total_area = 0.0
        # for peak in fine_spec.peaks:
        #     if peak[0] < 18*60:
        #         total_area += fine_spec.integrate_peak(peak[0])
        # # convert back to min
        # total_area = total_area/60
        # rel_purity = AUC_target / total_area

        # weight = 0.7
        # const = 0.1  # to adjust rel. yield to range of approx. 0-1
        # fitness = weight * const * rel_yield + (1 - weight) * rel_purity
        # self.logger.info(f'Area: {rel_yield}, Purity: {rel_purity}')
        # return {objective: fitness}

        return fitness
