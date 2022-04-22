"""
Generic interface class for all steps dedicated for analysis.
"""

from abc import abstractmethod

from xdl.steps.base_steps import AbstractStep

from chemputerxdl.steps.base_step import ChemputerStep

class AbstactAnalyzeStep(ChemputerStep, AbstractStep):
    """Abstract step to run the analysis.

    Args:
        vessel (str): Name of the vessel containing the analyte.
        sample_volume (float): Volume of the product sample to be sent to the
            analytical instrument. If not given - no sample is taken and the
            analysis performed as is (i.e., assuming contactless or immersion
            probe).
        dilution_volume (float): Volume of the solvent used to dilute the
            sample before analysis. If not given - no dilution is performed.
        dilution_solvent (str): Solvent used to dilute the sample if
            dilution_volume is given.
        cleaning_solvent (str): Solvent used to clean the analytical instrument
            (if analyte was sampled) and/or dilution vessel (if dilution was
            performed).
        method (str): Method used for the analysis. Defines the instrument to
            be used.
        method_properties (dict): Dictionary with additional properties, passed
            to the low-level analysis step.
    """

    def __init__(self):
        pass

    @abstractmethod
    def get_preparation_steps(self):
        """Gets steps required to prepare the mixture prior to analysis.

        Preparation steps are unique depending on the initial material location
        e.g. filter/flask/reactor and analytical instrument in use.

        Such steps might include: cooling reaction mixture; dissolving
        precipitate; drying material; etc.

        RESERVED FOR FUTURE USE!
        """

    @abstractmethod
    def get_analysis_steps(self):
        """Gets steps required to acquire the analytical data.

        Steps are unique for the given instrument.
        """

    @abstractmethod
    def get_postanalysis_steps(self):
        """Gets steps required after the data's been acquired.

        Steps are unique for the given instrument.
        """

    def get_sampling_steps(self):
        """Gets steps required to acquire the sample.

        Basically a given volume + some access is transferred to the syringe
        and slowly injected into the instrument.
        """

    def get_cleaning_steps(self):
        """Gets steps required to clean the instrument (and dilution vessel).
        """
