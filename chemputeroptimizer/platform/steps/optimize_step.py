"""
The module contains a wrapper step used to target desired step and its
properties for optimization.
"""

from typing import List

from xdl.errors import XDLError
from xdl.constants import JSON_PROP_TYPE
from xdl.steps.base_steps import AbstractStep, Step
from chemputerxdl.steps.base_step import ChemputerStep


class OptimizeStep(ChemputerStep, AbstractStep):
    """Wrapper for a step to be optimised.

    Check the .constants module for the supported steps and their properties.

    Args:
        id (str): ID to keep track of what parameters are being optimised.
        children (List): list of wrapped steps. Must be 1!
        optimize_properties (JSON_PROP_TYPE): json-like dictionary of the target
            properties for the optimization and their limits, e.g.
            optimize_properties="{'mass': {'max_value': 1, 'min_value': 0.5}}".

    Example:
        ...
        <OptimizeStep
            id="0"
            optimize_properties="{'mass': {'max_value': 1, 'min_value': 0.5}}"
                <AddSolid
                    "reagent"="reagent"
                    "mass"="mass"
                <AddSolid />
        <OptimizeStep />
        ...
    """

    PROP_TYPES = {
        'id': str,
        'children': List,
        'optimize_properties': JSON_PROP_TYPE,
    }

    def __init__(
            self,
            id: str,
            children: List[Step],
            optimize_properties: JSON_PROP_TYPE,
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
