"""
XDL step to execute the Raman instrument. Based on the OceanOpticsRaman
implementation from the AnalyticalLabware.
"""

from typing import Optional, Callable

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

        self.background_path = None

        for key, value in kwargs.items():
            setattr(self, key, value)

    def locks(self, chempiler):
        return [], [], []

    def execute(self, chempiler: 'Chempiler', logger=None, level=0):
        raman = chempiler[self.raman]

        if self.background_path:
            raman.spectrum.load_data(self.background_path)
            if raman.spectrum.reference is None:
                raman.spectrum.reference = raman.spectrum.y

        if self.blank:
            raman.obtain_reference_spectrum()
        # Else just upload the spectrum
        else:
            raman.get_spectrum()

            # save raw data
            fname = f'{chempiler.exp_name}_{raman.spectrum.timestamp}_raw'
            raman.spectrum.save_data(filename=fname, verbose=True)

            raman.spectrum.default_processing()

        if self.on_finish:
            self.on_finish(raman.spectrum.copy())
        return True
