from typing import Any, Tuple, Dict
from time import sleep, strftime
from xdl.steps.base_steps import AbstractBaseStep

# time the IDEX valve is left in sampling position
SAMPLE_TIME = 60 # seconds

# delay between checking the instrument status
CHECK_STATUS_INTERVAL = 10 # seconds

class RunHPLC(AbstractBaseStep):

    PROP_TYPES = {
        'hplc': str,
        'valve': str,
        'on_finish': Any,
        'is_cleaning': bool,
    }

    def __init__(
            self,
            hplc: str,
            valve: str,
            on_finish: Any,
            is_cleaning: bool = False,
            **kwargs
    ):
        super().__init__(locals())

        for key, value in kwargs.items():
            setattr(self, key, value)

    def locks(self, chempiler):
        return [], [], []

    def execute(self, chempiler: 'Chempiler', logger=None, level=0):
        hplc = chempiler[self.hplc]
        idex = chempiler[self.valve]

        # Handle cleaning and file name
        if self.is_cleaning:
            hplc.switch_method(self.cleaning_method)
            fname = f"BLANK_{chempiler.exp_name}_{strftime(r'%Y-%m-%d-%H-%M')}"
        else:
            hplc.switch_method(self.run_method)
            fname = f"RUN_{chempiler.exp_name}_{strftime(r'%Y-%m-%d-%H-%M')}"

        # prepare run
        hplc.preprun()

        # wait until ready
        while not hplc.status()[0] == 'PRERUN':
            sleep(CHECK_STATUS_INTERVAL)
        
        # start run
        hplc.run_method(hplc.data_dir, fname)
        idex.sample(SAMPLE_TIME)

        # wait until run is finished
        while not hplc.status()[0] == 'PRERUN':
            sleep(CHECK_STATUS_INTERVAL)

        hplc.standby()

        hplc.get_spectrum()
        
        # processing individual spectrums
        for spectrum in hplc.spectra:
            hplc.spectra[spectrum].default_processing()

        # copying
        spectra = {
            channel: spectrum.copy()
            for channel, spectrum in hplc.spectra.items()
        }
        self.on_finish(spectra)
        return True
