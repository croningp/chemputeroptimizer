"""
XDL step to run the analysis with an OceanInsight (Ocean Optics) Raman
Spectrometer. The implementation is based on the
AnalyticalLabware.devices.oceanoptics.raman module.
"""

from typing import Callable

from AnalyticalLabware.devices.OceanOptics.Raman.raman_spectrum import (
    RamanSpectrum,
)

from xdl.steps.base_steps import AbstractBaseStep


class RunRaman(AbstractBaseStep):

    PROP_TYPES = {
        'raman': str,
        'on_finish': Callable[[RamanSpectrum], None],
        'blank': bool,
        'background_path': str,
    }

    def __init__(
            self,
            raman: str,
            on_finish: Callable[[RamanSpectrum], None] = None,
            blank: bool = False,
            background_path: Optional[str] = None,
            **kwargs
    ):
        super().__init__(locals())

    def locks(self, chempiler):
        return [], [], []

    def execute(self, chempiler: 'Chempiler', logger=None, level=0):
        """Measure raman spectrum and pass the result to on_finish."""

        raman: OceanOpticsRaman = chempiler[self.raman]

        # If the background path is given, load the data and store it as
        # A new reference
        if self.background_path:
            raman.spectrum.load_data(self.background_path)
            reference = raman.spectrum.y

        # If blank - just update the reference
        if self.blank:
            raman.obtain_reference_spectrum()
        # Else just upload the spectrum
        else:
            raman.get_spectrum()
        raman.spectrum.default_processing()
        if self.on_finish is not None:
            self.on_finish(raman.spectrum.copy())
        return True
