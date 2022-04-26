"""Running test on Dilute step with various graphs."""

# pylint: disable-all

from pathlib import Path
from random import sample

import pytest

from chemputeroptimizer.platform.steps.steps_sample.utils import (
    NoDilutionVessel,
)

from ..utils import (
    get_chempiler,
    generic_optimizer_test,
    remove_chempiler_files,
    remove_all_logs,
    get_prepared_xdl,
)


HERE = Path(__file__).parent
FILES = HERE.parent.joinpath('files')

XDL = FILES.joinpath('xdl', 'dilute_sample.xdl').absolute().as_posix()
GRAPHS = FILES.joinpath('graph').glob('graph_dilute_*')

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
    # Should fail with "not_okay" graph
    try:
        xdl = get_prepared_xdl(XDL, graph)
    except NoDilutionVessel:
        # Should fail with "*_not_okay.json" graph
        assert 'not_okay' in graph
        return

    # Validate execution
    xdl.execute(chempiler)
