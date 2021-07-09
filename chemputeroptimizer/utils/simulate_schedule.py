"""Utility module for simulating parallel xdl scheduling"""

import copy
from typing import List, Union
from types import ModuleType

from networkx import MultiDiGraph

from xdl import XDL
from xdl.steps import Step
from xdl.hardware import Hardware
from xdl.utils.graph import get_graph


def simulate_schedule(
    xdls: List[XDL],
    graph: Union[str, MultiDiGraph],
    device_modules: List[ModuleType] = [],
    **kwargs
) -> XDL:

    """Simulate scheduled parallel xdls.

    Just concatenate given xdls, with corresponding hardware and reagents
    """

    graph = get_graph(graph)

    xdl_steps = []

    for xdl in xdls:
        for step in xdl.steps:
            xdl_steps.append(copy.deepcopy(step))

    added_reagents = []
    xdl_reagents = []
    xdl_hardware = []
    for xdl in xdls:
        for reagent in xdl.reagents:
            if reagent.name not in added_reagents:
                xdl_reagents.append(reagent)
                added_reagents.append(reagent.name)

        for component in xdl.hardware:
            new_component = copy.deepcopy(component)
            xdl_hardware.append(new_component)

    # Make XDL object and return it
    xdl_obj = XDL(
        steps=xdl_steps,
        reagents=xdl_reagents,
        hardware=Hardware(xdl_hardware)
    )
    return xdl_obj
