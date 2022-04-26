"""Running tests on 10 random configurations and analytical instruments."""

# pylint: disable-all

from pathlib import Path

import pytest

from ..utils import (
    get_chempiler,
    generic_optimizer_test,
    remove_chempiler_files,
    remove_all_logs,
    get_prepared_xdl,
)


HERE = Path(__file__).parent
FILES = HERE.parent.joinpath('files')

XDLS = FILES.joinpath('xdl').glob('nmr_analyze*')
NMR_GRAPH = FILES.joinpath('graph', 'nmr_analyze.json').absolute().as_posix()

@pytest.fixture
def chempiler():

    # Factory
    def _get_chempiler(graph):
        return get_chempiler(graph)

    yield _get_chempiler

    # Clean-up actions
    remove_all_logs()
    remove_chempiler_files()

@pytest.mark.unit
@pytest.mark.parametrize('xdl', XDLS)
def test_nmr_analyze(chempiler, xdl):

    # Path -> string
    xdl = xdl.absolute().as_posix()

    # Instantiating
    chempiler = chempiler(NMR_GRAPH)

    # Launching XDL
    xdl = get_prepared_xdl(xdl, NMR_GRAPH)

    # Testing
    xdl.execute(chempiler)
