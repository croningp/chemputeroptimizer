"""Collection of utility functions for analysis steps."""

import json
import time
import typing
from typing import Optional
from pathlib import Path

import AnalyticalLabware

from chemputerxdl.constants import CHEMPUTER_FLASK

from .constants import (
    SHIMMING_TIME_CHECK,
    SHIMMING_SOLVENTS,
)

if typing.TYPE_CHECKING:
    from networkx import MultiDiGraph


SHIMMING_RESULTS_RELATIVE_PATH = Path(
    'devices',
    'Magritek',
    'Spinsolve',
    'utils',
)

def check_last_shimming_results() -> bool:
    """ Returns the result of the last shimming.

    If False - shimming is required, otherwise True. The function checks for
    the .json file with the last shimming results. This option was included in
    the latest version of AnalyticalLabware and atm is the only way to store
    the latest state of the Spinsolve NMR without accessing the instruments
    module.

    If such file is absent, i.e. shimming was not performed yet, returns False.
    """
    #TODO check for better way
    analyticallabware_path = Path(AnalyticalLabware.__file__).parent
    shimming_results_filepath = analyticallabware_path.joinpath(
        SHIMMING_RESULTS_RELATIVE_PATH,
        'shimming.json'
    )

    try:
        with open(shimming_results_filepath) as fobj:
            last_shimming_results = json.load(fobj)
    except FileNotFoundError:
        return False

    # timecheck
    now = time.time()

    if now - last_shimming_results['timestamp'] > SHIMMING_TIME_CHECK: # 24 h
        return False

    return True

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
