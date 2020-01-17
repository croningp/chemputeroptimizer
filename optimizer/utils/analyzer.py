"""
Module for comparing several spectra.
"""

class SpectraAnalyzer():
    """General class for analyzing spectra differences.
    
    Class provides methods to compare several spectra, classify the peaks
    accoring their changes in time (e.g. starting material, intermediate,
    product or noise) and give the relative information on yield and purity,
    when reference information is supplied.

    Attributes:
        max_spectra (int): Maximum number of spectra to analize.
        data_path (str): Valid path to load spectra from.
    """

    def __init__(self, max_spectra, data_path):
        
        self.max_spectra = max_spectra
        self.data_path = data_path

        # Variables to store spectral data
        self.current_spectrum = None
        self.last_spectrum = None
        self.spectra = None

        # Future arguments for peaks classification
        self.starting_material = None
        self.intermediate = None
        self.final_product = None
    
    def load_spectrum(self, spectrum):
        """Loads the spectrum and stores and as current_spectrum.
        
        Args:
            spectrum (Dict): A dictionary containing spectral data obtained from
            an analytical instrument. Example:
            {
                "<x_axis>": [...],
                "<y_axis>": [...],
                ...
                "peaks": {
                    "peak_ID": {
                        "coordinates": (peak_y, peak_x), 
                        "width": (left_x, right_x),
                        "area": peak_area,
                    }
                }
            }
        """

    def add_spectrum(self, spectrum):
        """Updates the latest spectrum.

        The previously measured spectrum stored in self.last_spectrum.
        
        Args:
            spectrum (Dict): A dictionary containing spectral data, see example in
            self.load_spectrum.__doc__.
        """

    def spectra_difference(self):
        """Compares two most recent spectra.

        Subtract two spectra and give an average difference based on integration of the
        result.

        Returns:
            (float): An average difference between spectra.
        """

    def final_analysis(self, reference, target=None):
        """Analyses the spectrum relative to provided reference.
        
        Args:
            reference (Any): A peak position (e.g. x coordinate) of the
                reference substance to compare to.
            target (Any, optional): A peak position of the target compound
                (i.e. product). If not supplied, the target will be selected automatically
                from peak classification.
        """
        
    def get_yield(self, params):
        """Calculates yield of the final product.
        
        Args:
            params (Dict): Final analysis parameter dictionary, containg information
                to calculate the yield, i.e. sample volume and reference concentration.
        """

    def get_purity(self, product=None):
        """Calculates the purity of the final product.
        
        Args:
            product (Any, optional): An a analytical data for the final product, e.g. reference 
                peak or full spectrum. If not supplied, will use the spectral data obtained during 
                reaction monitoring and classified as product.
        """
    
    def classify_peaks(self):
        """Classifies peaks according to their changes in time."""

    def _filter_noise(self, threshold=None):
        """Filters the peaks classified as noise.
        
        Peaks are classified as noise if an average difference in time
        for the peak area is below the supplied threshold.

        Args:
            threshold (float, optional): An arbitrary threshold to classify peak as noise.
                If not supplied, will be chosen as a standard deviation for peaks,
                classified as valid (e.g. product or starting material).
        """

    def _get_ascending(self):
        """Classifies peaks with increasing area over time."""

    def _get_descending(self):
        """Classifies peaks with decreasing area over time."""

    def _dump(self):
        """Dumps the first spectrum as csv if maximum number of spectra 
            reaches max_spectra."""
