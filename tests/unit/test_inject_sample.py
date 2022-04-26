"""Running test on Dilute step with various graphs."""

# pylint: disable-all

from pathlib import Path
from random import sample

import pytest

from chemputeroptimizer.platform.steps import InjectSample

from ..utils import (
    get_chempiler,
    remove_chempiler_files,
    remove_all_logs,
    get_prepared_xdl,
)


HERE = Path(__file__).parent
FILES = HERE.parent.joinpath('files')

XDL = FILES.joinpath('xdl', 'inject_sample.xdl').absolute().as_posix()
GRAPHS = FILES.joinpath('graph').glob('graph_inject_*')

SMALL_VOLUME_FP = 'small_volume'

@pytest.fixture
def chempiler():

    # Factory
    def _get_chempiler(graph):
        return get_chempiler(graph)

    yield _get_chempiler

    # Clean-up actions
    remove_all_logs()
    remove_chempiler_files()

@pytest.mark.integration
@pytest.mark.parametrize('graph', GRAPHS)
def test_dilute_step(chempiler, graph):

    # Path to string
    graph = graph.absolute().as_posix()

    # Instantiating
    chempiler = chempiler(graph)

    # Launching XDL
    xdl = get_prepared_xdl(XDL, graph)

    # Checking correct sample excess volume for smaller syringe
    if SMALL_VOLUME_FP in graph:
        for step in xdl.steps:
            if isinstance(step, InjectSample):
                # For 5 mL syringe and 4 mL sample
                assert step.sample_excess_volume == 1

    # Validate execution
    xdl.execute(chempiler)
