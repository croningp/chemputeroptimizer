from typing import Callable, Any

from xdl.steps.base_steps import AbstractBaseStep

class RunRaman(AbstractBaseStep):

    PROP_TYPES = {
        'raman': str,
        'on_finish': Any,
        'blank': bool,
    }

    def __init__(
        self,
        raman: str,
        on_finish: Any,
        blank: bool = False,
        **kwargs
    ):
        super().__init__(locals())

    def locks(self, chemplier):
        return [], [], []

    def execute(self, chempiler: 'Chempiler', logger=None, level=0):
        raman = chempiler[self.raman]
        if self.blank:
            raman.obtain_reference_spectrum()
        else:
            raman.get_spectrum()
        spec = raman.spectrum.default_process(chempiler.output_dir)
        self.on_finish(spec)
