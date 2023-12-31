"""
XDL step to execute the NMR instrument. Based on the Margitek Spinsolve NMR
implementation from the AnalyticalLabware.
"""

import typing
from typing import Callable

from xdl.steps.base_steps import AbstractBaseStep
from xdl.constants import JSON_PROP_TYPE


if typing.TYPE_CHECKING:
    from chempiler import Chempiler
class RunNMR(AbstractBaseStep):

    PROP_TYPES = {
        'nmr': str,
        'on_finish': Callable,
        'protocol': str,
        'protocol_options': JSON_PROP_TYPE,
    }

    DEFAULT_PROPS = {
        # anonymous function to take 1 argument and return None
        'on_finish': lambda spec: None,
        'protocol_options': {}
    }

    def __init__(
        self,
        nmr: str,
        on_finish: Callable = 'default',
        protocol: str = None,
        protocol_options: JSON_PROP_TYPE = 'default',
        **kwargs
    ):
        super().__init__(locals())

    def locks(self, chempiler):
        return [], [], []

    def execute(
        self,
        chempiler: 'Chempiler',
        logger=None,
        level=0,
        **kwargs
    ) -> bool:
        nmr = chempiler[self.nmr]
        #FIXME fix the attribute type for the get_spectrum
        # to avoid check None is None and (None, None) is not None
        if self.protocol is not None:
            nmr.get_spectrum((self.protocol, self.protocol_options)) # Tuple!
        else:
            nmr.get_spectrum(None)
        nmr.spectrum.default_processing()
        if self.on_finish is not None:
            self.on_finish(nmr.spectrum.copy())

        return True
