""" Utility function for the Optimizer and Optimize Dynamic Step."""

import typing
import copy
from typing import Optional, Union
from itertools import chain
from logging import Logger

from xdl import XDL
from xdl.hardware import Hardware
from xdl.constants import INERT_GAS_SYNONYMS

from chemputerxdl.constants import (
    CHEMPUTER_FLASK,
    CHEMPUTER_WASTE,
)
from chemputerxdl.utils.execution import get_vessel_stirrer

from ...constants import ANALYTICAL_INSTRUMENTS
from .steps_analysis.constants import SHIMMING_SOLVENTS

# For type annotations
if typing.TYPE_CHECKING:
    from xdl.steps import Step
    from networkx import MultiDiGraph


# For volume tracking
SAFETY_EXCESS_VOLUME = 1.5  # 20 %

# Input messages
USER_INPUT_MESSAGE = 'Please {} {} and press Enter to continue\n'

def deep_copy_step(step: 'Step'):
    """Deprecated. Step.__deepcopy__ now implemented so you can just do
    ``copy.deepcopy(step)``. This remains here for backwards compatibility
    but should eventually be removed.

    Return a deep copy of a step. Written this way with children handled
    specially for compatibility with Python 3.6.
    """
    # Copy children
    children = []
    if 'children' in step.properties and step.children:
        for child in step.children:
            children.append(deep_copy_step(child))

    # Copy properties
    copy_props = {}
    for k, v in step.properties.items():
        if k != 'children':
            copy_props[k] = v
    copy_props['children'] = children

    # Make new step
    copied_step = type(step)(**copy_props)

    return copied_step

def xdl_copy(xdl_obj: 'XDL') -> 'XDL':
    """Deprecated. XDL.__deepcopy__ now implemented so you can just do
    ``copy.deepcopy(xdl_obj)``. This remains here for backwards compatibility
    but should eventually be removed.

    Returns a deepcopy of a XDL object. copy.deepcopy can be used with
    Python 3.7, but for Python 3.6 you have to use this.

    Args:
        xdl_obj (XDL): XDL object to copy.

    Returns:
        XDL: Deep copy of xdl_obj.
    """
    copy_steps = []
    copy_reagents = []
    copy_hardware = []

    # Copy steps
    for step in xdl_obj.steps:
        copy_steps.append(deep_copy_step(step))

    # Copy reagents
    for reagent in xdl_obj.reagents:
        copy_props = copy.deepcopy(reagent.properties)
        copy_reagents.append(type(reagent)(**copy_props))

    # Copy hardware
    for component in xdl_obj.hardware:
        copy_props = copy.deepcopy(component.properties)
        copy_hardware.append(type(component)(**copy_props))

    # Return new XDL object
    return XDL(steps=copy_steps,
               reagents=copy_reagents,
               hardware=Hardware(copy_hardware),
               logging_level=xdl_obj.logging_level,
               internal_platform=xdl_obj._internal_platform)

def find_instrument(graph: 'MultiDiGraph', method: str) -> Optional[str]:
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
        procedure: list['Step'],
        meaningful_steps: list['str']
    ) -> Optional['Step']:
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
        graph: 'MultiDiGraph'
    ) -> Optional[list[dict]]:
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
    graph: 'MultiDiGraph',
) -> Optional[list[dict]]:
    """Get the list of waste containers on the graph

    Returns:
        List[Dict]: list of waste nodes.
    """

    waste_containers = []

    for node, data in graph.nodes(data=True):
        if data['class'] == CHEMPUTER_WASTE:
            waste_containers.append(graph.nodes[node])

    return waste_containers

def get_dilution_flask(graph: 'MultiDiGraph') -> Optional[str]:
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

def get_flasks_for_dilution(graph: 'MultiDiGraph') -> Union[str, list]:
    """Get a list of empty flasks with a stirrers.

    Used to locate a flask to dilute the analyte before injecting into
    analytical instrument.
    """

    empty_flasks = [
        flask
        for flask, data in graph.nodes(data=True)
        if data['class'] == CHEMPUTER_FLASK and not data['chemical']
    ]

    empty_flasks_with_stirrers = [
        flask for flask in empty_flasks
        if get_vessel_stirrer(graph, flask)
    ]

    return empty_flasks_with_stirrers

def find_shimming_solvent_flask(
    graph: 'MultiDiGraph') -> Optional[tuple[str, float]]:
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

def extract_optimization_params(
    xdl: XDL,
    batch_size: int,
) -> dict[str, dict[str, dict[str, float]]]:
    """Get dictionary of all parameters to be optimized and pack it batchwise.

    Args:
        xdl (XDL):
    """

    parameters: dict[str, dict[str, dict[str, float]]] = {}

    # Getting general parameter set
    # It'll be same for all batches, but updated later batch-wise
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

    # Appending parameters batchwise
    for batch_number in range(1, batch_size + 1):
        parameters[f'batch {batch_number}'] = param_template

    return parameters

def forge_xdl_batches(
    xdl: XDL,
    parameters: dict[str, dict[str, dict[str, float]]],
) -> list[XDL]:
    """Create several xdls from their batches parameters.

    Args:
        xdl (XDL): Original xdl to take copies from.
        parameters (Dict[str, Dict[str, Dict[str, float]]]): Batch-wise nested
            dictionary with parameters for the xdl steps.

    Returns:
        List[XDL]: List of xdl objects, which differ by their parameters for
            optimization.
    """
    xdls: list[XDL] = []

    for batch_id, batch_params in parameters.items():

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

        # Appending batch id to the FinalAnalysis method if present
        for step in new_xdl.steps:
            if step.name == 'FinalAnalysis' or step.name == 'Analyze':
                step.properties['batch_id'] = batch_id

        xdls.append(new_xdl)

    return xdls

def get_volumes(graph: 'MultiDiGraph') -> dict[str, list[float, float]]:
    """
    Gets the map of flasks/wastes and their current volumes from the graph.
    """

    volumes = {}

    reagent_flasks = get_reagent_flasks(graph=graph)
    waste_containers = get_waste_containers(graph=graph)

    for container in chain(reagent_flasks, waste_containers):
        volumes[container['name']] = [
            container['current_volume'],
            container['max_volume']
        ]

    return volumes

def check_volumes(
    graph: 'MultiDiGraph',
    previous_volumes: dict[str, list[float, float]],
    logger: Logger,
) -> bool:
    """Checks volumes in flasks and waste containers.

    Prompts user input if not enough material/space available.

    Args:
        graph (MultiDiGraph): networkx MutliDiGraph object from the current
            state of the chemputer run.
        previous_volumes (dict): Mapping of reagent flasks and waste containers
            with their volumes, recorded previously.
        logger (Logger): Logger object to keep the record.
    """

    # Get new list of volumes
    new_volumes = get_volumes(graph=graph)

    for container, (current_volume, max_volume) in new_volumes.items():
        try:
            # Calculate the difference
            volume_diff = current_volume - previous_volumes[container][0]
            logger.info(
                'Volume change in %s is %.2f ml, current volume is %.2f',
                container,
                volume_diff,
                current_volume
            )

            # If material was used and insufficient amount left
            if (volume_diff < 0 and
                abs(volume_diff) * SAFETY_EXCESS_VOLUME > current_volume):

                # Ask to refill
                input(USER_INPUT_MESSAGE.format('refill', container))

                # Update the volume after user input
                previous_volumes[container][0] = max_volume
                # And in the graph
                graph.nodes[container]['current_volume'] = max_volume

            # If contanier filled and not enough space left
            elif (volume_diff > 0 and
                  volume_diff * SAFETY_EXCESS_VOLUME > \
                    max_volume - current_volume):

                # Ask to empty
                input(USER_INPUT_MESSAGE.format('empty', container))

                # Update the volume after user input
                previous_volumes[container][0] = 0
                # And in the graph
                graph.nodes[container]['current_volume'] = 0

            # Just update the volume tracking dictionary
            else:
                previous_volumes[container][0] += volume_diff

        except KeyError:
            logger.critical('Container %s not found in the volume map.')

    return True
