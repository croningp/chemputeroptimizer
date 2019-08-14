import random
from typing import List, Callable

from xdl.steps.base_steps import AbstractStep, AbstractDynamicStep, Step
from xdl.steps import HeatChill, HeatChillToTemp, Wait, StopHeatChill, Transfer
from xdl.steps.steps_analysis import RunNMR
from typing import Dict

class OptimizeStep(AbstractDynamicStep):
    """Wrapper for a step to run it and detect when the step is complete by NMR.
    Also contains flags to highlight which parameters in the step should be
    optimised. Multiple parameters to optimise can be specified, i.e. time and
    temp both set to True.

    Steps supported:
        temp: Any step with 'temp' property, e.g. HeatChill, HeatChillToTemp
        time: HeatChill, Wait
        volume: Any step with volume property, e.g. Add
    """
    def __init__(
        self,
        id: str,
        children: List[Step],
        nmr: str,
        on_nmr_finish: Callable,
        time: bool = True,
        temp: bool = False,
        volume: bool = False,
        nmr_delta: float = 1
    ):
        super().__init__(locals())
        try:
            assert len(children) == 1
        except AssertionError as e:
            raise AssertionError('Only one step can be wrapped by OptimizeStep.')
        self.step = children[0]
        self.state = {
            'current_nmr': [],
            'done': False,
        }

    def on_nmr_finish_wrapper(self, result):
        if abs(self.state['current_nmr'] - result) < self.nmr_delta:
            self.state['done'] = True
        self.state['current_nmr'] = result

        self.on_nmr_finish(result)

    def on_start(self):
        if not self.time:
            return self.children

        if type(self.step) == HeatChill:
            return [
                HeatChillToTemp(self.step.vessel, self.step.temp, stir=self.step.stir)
            ]

        elif type(self.step) == Wait:
            return []

    def on_continue(self):
        if self.state['done'] or not self.time:
            return []

        return [
            self.RunNMR(nmr=self.nmr, on_finish=self.on_nmr_finish)
        ]

    def on_finish(self):
        if not self.time:
            return []

        if type(self.step) == HeatChill:
            return [
                StopHeatChill(vessel=self.step.vessel)
            ]
        
        elif type(self.step) == Wait:
            return []

            
def linspace(start, stop, step):
    vals = []
    x = start
    while x < stop:
        vals.append(x)
        x += step
    return vals


class Optimizer(AbstractDynamicStep):
    """Outer level wrapper for optimizing multiple parameters in an entire
    procedure.

    <Optimizer>
        <Add  ... />
        <OptimizeStep ... >
            <HeatChill ... />
        </OptimizeStep>
        ...
    </Optimizer>
    """
    def __init__(
        self,
        children: List[Step],
        n_iterations: List[float]
    ):
        self.results = {}
        self.used_params = []
        self.state = {
            'optimum_times': [],
            'iteration': 1,
        }

    def get_optimized_steps(self):
        optimized_steps = []
        for step in self.children:
            if type(step) == OptimizeStep:
                optimized_steps.append(step)
        return optimized_steps

    def get_params_template(self):
        optimized_steps = self.get_optimized_steps()
        params = {}
        for step in optimized_steps:
            if step.temp:
                params[f'{step.id}_temp'] = {
                    'min': step.min_temp, 'max': step.max_temp, type: 'temp'}
            if step.volume:
                params[f'{step.id}_volume'] = {
                    'min': step.min_volume, 'max': step.max_volume, type: 'temp'}
        return params

    def get_random_params(self):
        template = self.get_params_template()
        params = {}
        for param in template:
            params[param] = random.randint(int(param['min']), int(param['max']))
        return params

    def on_start(self):
        return []

    def on_continue(self):
        if self.state['iteration'] >= self.n_iterations:
            return []

        self.state['params'] = self.get_random_params()
        params = self.state['params']
        for step in self.children:
            if type(step) == OptimizeStep:
                if step.time:
                    step.on_nmr_finish = self.on_optimize_time_nmr_finish

                if step.temp:
                    step.step.temp = params[f'{step.id}_temp']

                if step.volume:
                    step.step.volume = params[f'{step.id}_volume']
        
        self.state['iteration'] += 1

        return self.children + [
            Transfer(from_vessel=self.final_vessel, to_vessel=self.nmr, volume=self.nmr_volume),
            RunNMR(nmr=self.nmr, on_finish=self.on_nmr_finish),
        ] + self.cleaning_steps()

    def on_finish(self):
        return []
