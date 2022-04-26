"""Running tests on 10 random configurations and analytical instruments."""

# pylint: disable-all

from pathlib import Path

import pytest

from ..utils import (
    get_chempiler,
    remove_chempiler_files,
    remove_all_logs,
    get_prepared_xdl,
    remove_xdlexes,
)


HERE = Path(__file__).parent
FILES = HERE.parent.joinpath('files')

XDLS = FILES.joinpath('xdl').glob('nmr_analyze*.xdl')
NMR_GRAPH = FILES.joinpath('graph', 'graph_nmr_analyze.json').absolute().as_posix()

@pytest.fixture
def chempiler():

    # Factory
    def _get_chempiler(graph):
        return get_chempiler(graph)

    yield _get_chempiler

    # Clean-up actions
    remove_all_logs()
    remove_chempiler_files()

@pytest.fixture
def xdl():

    def _get_xdl(xdl_file, graph):
        return get_prepared_xdl(xdl_file, graph)

    yield _get_xdl

    remove_xdlexes(FILES.joinpath('xdl').absolute())

@pytest.mark.unit
@pytest.mark.parametrize('xdl_file', XDLS)
def test_nmr_analyze(chempiler, xdl, xdl_file):

    # Path -> string
    xdl_file = xdl_file.absolute().as_posix()

    # Instantiating
    chempiler = chempiler(NMR_GRAPH)
    xdl = xdl(xdl_file, NMR_GRAPH)

    # Testing
    xdl.execute(chempiler)
