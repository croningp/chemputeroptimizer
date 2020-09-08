"""
XDL step to execute the NMR instrument. Based on the Margitek Spinsolve NMR
implementation from the AnalyticalLabware.
"""

from typing import Any, Tuple, Dict

from xdl.steps.base_steps import AbstractBaseStep
from xdl.constants import JSON_PROP_TYPE


class RunNMR(AbstractBaseStep):

    PROP_TYPES = {
        'nmr': str,
        'on_finish': Any,
        'protocol': str,
        'protocol_options': JSON_PROP_TYPE,
    }

    def __init__(
            self,
            nmr: str,
            on_finish: Any,
            protocol: str = None,
            protocol_options: JSON_PROP_TYPE = None,
            **kwargs
    ):
        super().__init__(locals())

    def locks(self, chempiler):
        return [], [], []

    def execute(self, chempiler: 'Chempiler', logger=None, level=0):
        nmr = chempiler[self.nmr]
        nmr.get_spectrum((self.protocol, self.protocol_options)) # Tuple!
        spec = nmr.spectrum.default_processing()
        self.on_finish(spec)
        return True
