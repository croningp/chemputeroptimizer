"""
Special XDL step to perform the Spinsolve NMR shimming.
"""
import typing
from typing import Optional

from xdl.steps.base_steps import AbstractBaseStep

if typing.TYPE_CHECKING:
    from chempiler import Chempiler


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
