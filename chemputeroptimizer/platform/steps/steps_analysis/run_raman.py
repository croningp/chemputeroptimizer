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
    }

    def __init__(
            self,
            raman: str,
            on_finish: Callable[[RamanSpectrum], None] = None,
            blank: bool = False,
            **kwargs
    ):
        super().__init__(locals())

    def locks(self, chemplier):
        return [], [], []

    def execute(self, chempiler: 'Chempiler', logger=None, level=0):
        raman = chempiler[self.raman]
        if self.blank:
            raman.obtain_reference_spectrum()
        else:
            raman.get_spectrum()
        raman.spectrum.default_processing()
        if self.on_finish is not None:
            self.on_finish(raman.spectrum.copy())
        return True
