from typing import List, Callable, Optional, Dict, Any

from xdl.utils.errors import XDLError
from xdl.steps.base_steps import AbstractStep, Step


class OptimizeStep(AbstractStep):
    """Wrapper for a step to be optimised

    Steps and parameters supported:
        Add: addition volume
        HeatChill, HeatChillToTemp: reaction temperature
        HeatChill, Wait, Stir: reaction time

    Args:
        id (str): ID to keep track of what parameters are being optimised.
        children (List[Step]): List of steps to optimize parameters for.
            Max length 1. Reason for using a list is for later integration into
            XDL.
        max_value (float): Minimum parameter value for the optimization routine.
        min_value (float): Maximum parameter value for the optimization routine.
    
    Example:
        ...
        <OptimizeStep "max_value"=1.2, "min_value"=3.2
            <Add
                "reagent"="reagent"
                "volume"=volume
            <Add />
        <OptimizeStep />
        <OptimizeStep "max_value"=70, "min_value"=25
            <HeatChill "temp"=temperature />
        <OptimizeStep />
        ...
    """

    PROP_TYPES = {
        'id': str,
        'children': List,
        'optimize_properties': Dict,
    }

    def __init__(
            self,
            id: str,
            children: List[Step],
            optimize_properties: Dict,
            **kwargs
        ):
        super().__init__(locals())

        # Check there is only one child step.
        if len(children) > 1:
            raise XDLError('Only one step can be wrapped by OptimizeStep.')

        self.step = children[0]

    def _get_optimized_parameters(self):
        pass

    def _check_input(self):
        pass

    def get_steps(self):
        return self.children

    def human_readable(self, language='en'):
        return 'Optimize ' + self.step.human_readable()
