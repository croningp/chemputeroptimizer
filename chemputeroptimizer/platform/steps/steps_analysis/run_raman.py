from typing import Optional, Callable, Any

from xdl.steps.base_steps import AbstractBaseStep


class RunRaman(AbstractBaseStep):

    PROP_TYPES = {
        'raman': str,
        'on_finish': Callable,
        'blank': bool,
    }

    def __init__(
            self,
            raman: str,
            on_finish: Optional[Callable] = None,
            blank: bool = False,
            **kwargs
    ):
        super().__init__(locals())

    def locks(self, chemplier):
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
        else:
            raman.get_spectrum()

            # save raw data
            fname = f'{chempiler.exp_name}_{raman.spectrum.timestamp}_raw'
            raman.spectrum.save_data(filename=fname, verbose=True)

            # processing
            raman.spectrum.reference = reference
            raman.spectrum.subtract_reference()
            raman.spectrum.default_processing()

        if self.on_finish:
            self.on_finish(raman.spectrum.copy())

        return True
