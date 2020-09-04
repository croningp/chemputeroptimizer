from typing import Any, Tuple, Dict
from time import sleep
from xdl.steps.base_steps import AbstractBaseStep


class RunHPLC(AbstractBaseStep):

    PROP_TYPES = {
        'hplc': str,
        'valve': str,
        'on_finish': Any,
        'protocol': Tuple[str, Dict],
    }

    def __init__(
            self,
            hplc: str,
            valve: str,
            on_finish: Any,
            protocol: Tuple[str, Dict] = None,
            **kwargs
    ):
        super().__init__(locals())

    def locks(self, chempiler):
        return [], [], []

    def execute(self, chempiler: 'Chempiler', logger=None, level=0):
        hplc = chempiler[self.hplc]
        idex = chempiler[self.valve]
        hplc.switch_method(self.protocol)
        hplc.preprun()
        while not hplc.status()[0] == 'PRERUN':
            sleep(1)
        idex.sample(5)
        if self.protocol == 'AH_cleaning':
            sleep(5*60)
        else:
            sleep(30*60)
        hplc.standby()
        hplc.get_spectrum()
        spec = hplc.spectrum.default_processing()
        self.on_finish(spec)
        return True
