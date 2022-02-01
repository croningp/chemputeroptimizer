"""
The module contains a wrapper step used to target desired step and its
properties for optimization.
"""
import ast

from typing import List, Union

from xdl.errors import XDLError
from xdl.constants import JSON_PROP_TYPE
from xdl.steps.base_steps import AbstractStep, Step
from chemputerxdl.steps.base_step import ChemputerStep


class ConstrainedStep(ChemputerStep, AbstractStep):
    """Wrapper for a constrained Add step.

    Check the .constants module for the supported steps and their properties.

    Args:
        ids (List): IDs of OptimizeSteps that influence the parameter value
        parameter (str): which parameter is constrained, e.g. volume, time
        target (float): the target value, see example calculation below
        children (List): list of wrapped steps. Must be 1

    Example:
        ...
        <ConstrainedStep
            ids="[1, 2]"
            parameter="volume"
            target="50"
                <Add
                    "reagent"="toluene"
                    "vessel"="reactor"
                    "volume"="99999 mL"
                <Add />
        <ConstrainedStep />
        ...

        The volume of the Add step will then be calculated as in:
        V(target) = V(id1) + V(id2) + V(Add)
    """

    PROP_TYPES = {
        'ids': Union[List, str],
        'target': float,
        'parameter': str,
        'children': List,
    }

    def __init__(
            self,
            ids: Union[List, str],
            target: float,
            parameter: str,
            children: List[Step],
            **kwargs
        ):
        super().__init__(locals())

        # Check there is only one child step.
        if len(children) > 1:
            raise XDLError('Only one step can be wrapped by ConstrainedStep.')

        self.step = children[0]

        if isinstance(ids, str):
            self.ids = ast.literal_eval(ids)
            assert isinstance(self.ids, List)

    def _get_optimized_parameters(self):
        pass

    def _check_input(self):
        pass

    def get_steps(self):
        return self.children

    def human_readable(self, language='en'):
        return 'Constrained ' + self.step.human_readable()
