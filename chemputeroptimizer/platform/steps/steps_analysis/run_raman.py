"""
XDL step to execute the Raman instrument. Based on the OceanOpticsRaman
implementation from the AnalyticalLabware.
"""

from typing import Optional, Callable

from AnalyticalLabware.devices.OceanOptics.Raman.raman_spectrum import (
    RamanSpectrum,
)
from AnalyticalLabware.devices.OceanOptics.Raman.raman_control import (
    OceanOpticsRaman,
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
            on_finish: Optional[Callable[[RamanSpectrum], None]] = None,
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
            raman.spectrum.reference = raman.spectrum.y


        # If blank - just update the reference
        if self.blank:
            raman.obtain_reference_spectrum()
        # Else just upload the spectrum
        else:
            raman.get_spectrum()

            # save raw data
            fname = f'{chempiler.exp_name}_{raman.spectrum.timestamp}_raw'
            raman.spectrum.save_data(filename=fname, verbose=True)

            # processing
            if raman.spectrum.reference:
                raman.spectrum.subtract_reference()

            raman.spectrum.default_processing()

        if self.on_finish is not None:
            self.on_finish(raman.spectrum.copy())

        return True
