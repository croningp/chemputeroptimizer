from typing import List, Dict

from xdl.steps import Step
from xdl.constants import INERT_GAS_SYNONYMS

from chemputerxdl.utils.execution import get_vessel_stirrer

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

def get_reagent_flasks(
        graph: MultiDiGraph
    ) -> List[Dict]:
    """Get the list of reagent and solvent flasks from the graph

    Reagent and solvent flasks are assumed to have valid "chemical" attribute.

    Returns:
        List[Dict]: list of flasks nodes.
    """

    flasks_reagents = []

    for node, data in graph.nodes(data=True):
        try:
            if data['chemical'] not in INERT_GAS_SYNONYMS:
                flasks_reagents.append(graph.nodes[node])
        except KeyError:
            pass

    return flasks_reagents

def get_waste_containers(
    graph: MultiDiGraph,
) -> List[Dict]:
    """Get the list of waste containers on the graph

    Returns:
        List[Dict]: list of waste nodes.
    """

    waste_containers = []

    for node, data in graph.nodes(data=True):
        if data['class'] == 'ChemputerWaste':
            waste_containers.append(graph.nodes[node])

    return waste_containers

def get_dilution_flask(graph: MultiDiGraph) -> str:
    """ Get an empty flask with a stirrer attached to it.

        Used to dilute the analyte before injecting into analytical instrument.
    """

    empty_flasks = [
        flask
        for flask, data in graph.nodes(data=True)
        if data['class'] == 'ChemputerFlask' and not data['chemical']
    ]

    for flask in empty_flasks:
        # looking for stirrer attached
        found_stirrer = get_vessel_stirrer(graph, flask)

        # if found stirrer, return current flask
        if found_stirrer:
            return flask

    return None
