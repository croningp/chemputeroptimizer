"""
Special XDL step to perform the Spinsolve NMR shimming.
"""
import json
import os
import time
from typing import Optional

import AnalyticalLabware

from xdl.steps.base_steps import AbstractBaseStep

from .constants import SHIMMING_TIME_CHECK


SHIMMING_RESULTS_RELATIVE_PATH = os.path.join(
    'devices',
    'Magritek',
    'Spinsolve',
    'utils',
)

def check_last_shimming_results() -> bool:
    """ Returns the result of the last shimming.

    If False - shimming is required, otherwise True. The function checks for
    the .json file with the last shimming results. This option was included in
    the latest version of AnalyticalLabware and atm is the only way to store
    the latest state of the Spinsolve NMR without accessing the instruments
    module.

    If such file is absent, i.e. shimming was not performed yet, returns False.
    """
    #TODO check for better way
    analyticallabware_path = os.path.dirname(AnalyticalLabware.__file__)
    shimming_results_filepath = os.path.join(
        analyticallabware_path,
        SHIMMING_RESULTS_RELATIVE_PATH,
        'shimming.json'
    )

    try:
        with open(shimming_results_filepath) as fobj:
            last_shimming_results = json.load(fobj)
    except FileNotFoundError:
        return False

    # timecheck
    now = time.time()

    if now - last_shimming_results['timestamp'] > SHIMMING_TIME_CHECK: # 24 h
        return False

    return True

class ShimNMR(AbstractBaseStep):

    PROP_TYPES = {
        'nmr': str,
        'reference_peak': float,
        'option': str,
    }

    DEFAULT_PROPS = {
        'option': 'QuickShimAll',
    }

    def __init__(
            self,
            nmr: str,
            reference_peak: float,
            option: Optional[str] = 'default',
            **kwargs
    ) -> None:
        super().__init__(locals())

    def execute(self, chempiler: 'Chempiler', logger=None, level=0):
        instrument = chempiler[self.nmr]
        # just go on with simulation device
        if instrument.__class__.__name__.startswith('Sim'):
            return True
        instrument.shim_on_sample(
            reference_peak=self.reference_peak,
            option=self.option,
        )
        return True
