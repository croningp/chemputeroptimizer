""" Utility function for the Optimizer and Optimize Dynamic Step."""

from typing import List, Dict, Tuple, Optional, Any

from xdl.steps import Step
from xdl.constants import INERT_GAS_SYNONYMS
from xdl import XDL
from xdl.utils.copy import xdl_copy

from chemputerxdl.constants import (
    CHEMPUTER_FLASK,
    CHEMPUTER_WASTE,
)
from chemputerxdl.utils.execution import get_vessel_stirrer

from networkx import MultiDiGraph

from ...constants import ANALYTICAL_INSTRUMENTS
from .steps_analysis.constants import SHIMMING_SOLVENTS


def find_instrument(graph: MultiDiGraph, method: str) -> Optional[str]:
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
    ) -> Optional[Step]:
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
    ) -> Optional[List[Dict]]:
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
) -> Optional[List[Dict]]:
    """Get the list of waste containers on the graph

    Returns:
        List[Dict]: list of waste nodes.
    """

    waste_containers = []

    for node, data in graph.nodes(data=True):
        if data['class'] == CHEMPUTER_WASTE:
            waste_containers.append(graph.nodes[node])

    return waste_containers

def get_dilution_flask(graph: MultiDiGraph) -> Optional[str]:
    """ Get an empty flask with a stirrer attached to it.

        Used to dilute the analyte before injecting into analytical instrument.
    """

    empty_flasks = [
        flask
        for flask, data in graph.nodes(data=True)
        if data['class'] == CHEMPUTER_FLASK and not data['chemical']
    ]

    for flask in empty_flasks:
        # looking for stirrer attached
        found_stirrer = get_vessel_stirrer(graph, flask)

        # if found stirrer, return current flask
        if found_stirrer:
            return flask

    return None

def find_shimming_solvent_flask(
    graph: MultiDiGraph) -> Optional[Tuple[str, float]]:
    """
    Returns flask with the solvent suitable for shimming and corresponding
    reference peak in ppm.
    """

    # Map all chemicals with their flasks
    chemicals_flasks = {
        data['chemical']: flask
        for flask, data in graph.nodes(data=True)
        if data['class'] == CHEMPUTER_FLASK
    }

    # solvents for shimming
    shimming_solvents = chemicals_flasks.keys() & SHIMMING_SOLVENTS.keys()

    # iterating to preserve solvent priority in SHIMMING_SOLVENTS
    for solvent in SHIMMING_SOLVENTS:
        if solvent in shimming_solvents:
            return chemicals_flasks[solvent], SHIMMING_SOLVENTS[solvent]

    return None

def extract_optimization_params(xdl: XDL) -> Dict[str, Dict[str, Any]]:
    """Get dictionary of all parameters to be optimized.

    Updates parameters attribute in form:
        (Dict): Nested dictionary of optimizing steps and corresponding
            parameters of the form:
            {
                "step_ID-parameter": {
                    "max_value": <maximum parameter value>,
                    "min_value": <minimum parameter value>,
                    "current_value": <parameter value>,
                }
            }

    Example:
        {
            "HeatChill_1-temp": {
                "max_value": 70,
                "min_value": 25,
                "current_value": 35,
            }
        }
    """
    param_template = {}

    for i, step in enumerate(xdl.steps):
        if step.name == 'OptimizeStep':
            param_template.update(
                {
                    f'{step.children[0].name}_{i}-{param}': {
                        **step.optimize_properties[param],
                        'current_value': step.children[0].properties[param]
                    }
                    for param in step.optimize_properties
                }
            )

    return param_template

def forge_xdl_batches(
    xdl: XDL,
    parameters: Dict[str, Dict[str, Dict[str, float]]],
) -> List[XDL]:
    """Create several xdls from their batches parameters.

    Args:
        xdl (XDL): Original xdl to take copies from.
        parameters (Dict[str, Dict[str, Dict[str, float]]]): Batch-wise nested
            dictionary with parameters for the xdl steps.

    Returns:
        List[XDL]: List of xdl objects, which differ by their parameters for
            optimization.
    """
    xdls: List[XDL] = []

    for batch_id, batch_params in parameters:

        # Protect the original xdl
        new_xdl = xdl_copy(xdl)

        # Update the actual steps properties
        for record in batch_params:
            # Slicing for step index
            step_id = int(record[record.index('_') + 1:record.index('-')])
            # Slicing for parameter name
            param = record[record.index('-') + 1:]
            # Updating the parameter of the copied xdl
            # This step should be the OptimizeStep wrapper with its children
            # As the actual step to change the property
            new_xdl.steps[step_id].children[0].properties[param] = \
                parameters[batch_id][record]['current_value']

        xdls.append(new_xdl)

        return xdls
