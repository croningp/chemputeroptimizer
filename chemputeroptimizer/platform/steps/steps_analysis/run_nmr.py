from typing import Any, Tuple, Dict

from xdl.steps.base_steps import AbstractBaseStep


class RunNMR(AbstractBaseStep):

    PROP_TYPES = {
        'nmr': str,
        'on_finish': Any,
        'protocol': Tuple[str, Dict],
    }

    def __init__(
            self,
            nmr: str,
            on_finish: Any,
            protocol: Tuple[str, Dict] = None,
            **kwargs
    ):
        super().__init__(locals())

    def locks(self, chempiler):
        return [], [], []

    def execute(self, chempiler: 'Chempiler', logger=None, level=0):
        nmr = chempiler[self.nmr]
        nmr.get_spectrum(self.protocol)
        spec = nmr.spectrum.default_processing()
        self.on_finish(spec)
        return True
