from typing import Any, Tuple, Dict

from xdl.steps.base_steps import AbstractBaseStep


class RunHPLC(AbstractBaseStep):

    PROP_TYPES = {
        'hplc': str,
        'on_finish': Any,
        'protocol': Tuple[str, Dict],
    }

    def __init__(
            self,
            hplc: str,
            on_finish: Any,
            protocol: Tuple[str, Dict] = None,
            **kwargs
    ):
        super().__init__(locals())

    def locks(self, chempiler):
        return [], [], []

    def execute(self, chempiler: 'Chempiler', logger=None, level=0):
        hplc = chempiler[self.hplc]
        hplc.get_spectrum(self.protocol)
        spec = hplc.spectrum.default_processing()
        self.on_finish(spec)
        return True
