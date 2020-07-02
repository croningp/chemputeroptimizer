from typing import List

from xdl.steps import Step

from networkx import MultiDiGraph

from ...constants import ANALYTICAL_INSTRUMENTS


def find_instrument(graph: MultiDiGraph, method: str) -> str:
    """Get the analytical instrument for the given method

    Args:
        method (str): Name of the desired analytical method

    Returns:
        str: ID of the analytical instrument on the supplied graph
    """
    for node, data in graph.nodes(data=True):
        if data['class'] == ANALYTICAL_INSTRUMENTS[method]:
            return node

def find_nearest_waste(graph: MultiDiGraph, instrument: str) -> str:
    """Get the waste container closest to the given instrument.

    Args:
        instrument (str): Name of the analytical instrument.

    Returns:
        str: ID of the nearest waste container
    """

def find_last_meaningful_step(
        procedure: List[Step],
        meaningful_steps: List[str]
    ) -> Step:
    """Get the last step significant for the synthetic procedure.

    Mainly used for including of the FinalAnalysis step.

    Args:
        procedure (List[Step]): List of steps from the procedure.
        meaningful_steps (List[str]): List of names of "significant" steps.

    Returns:
        Tuple (int, Step): Last "significant" step and its index.
    """

    for i, step in enumerate(procedure[::-1]):
        if step.name in meaningful_steps:
            return len(procedure) - i, step
