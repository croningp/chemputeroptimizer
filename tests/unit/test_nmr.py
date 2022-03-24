"""Running tests on 10 random configurations and analytical instruments."""

# pylint: disable-all

from pathlib import Path
from random import sample

import pytest

from ..utils import (
    get_chempiler,
    get_chemputer_optimizer,
    generic_optimizer_test,
    remove_chempiler_files,
    remove_chemputeroptimizer_files,
    remove_all_logs,
)


HERE = Path(__file__).parent
FILES = HERE.parent.joinpath('files')

NMR_XDL = FILES.joinpath('xdl', 'nmr.xdl').absolute().as_posix()
NMR_GRAPH = FILES.joinpath('graph', 'nmr.json').absolute().as_posix()

# Config directory
CONFIGS = FILES.joinpath('config')
config_files = sample(list(CONFIGS.iterdir()), 10)

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
def chemputeroptimizer():

    # Factory
    def _get_chemputeroptimizer(xdl, graph):
        return get_chemputer_optimizer(xdl, graph)

    yield _get_chemputeroptimizer

    # Clean-up
    remove_all_logs()
    remove_chemputeroptimizer_files()

@pytest.mark.integration
@pytest.mark.parametrize('config', config_files[:])
def test_nmr_optimizer(chempiler, chemputeroptimizer, config):
    # Instantiating
    chempiler = chempiler(NMR_GRAPH)
    chemputeroptimizer = chemputeroptimizer(NMR_XDL, NMR_GRAPH)
    # Testing
    generic_optimizer_test(
        chempiler=chempiler,
        chemputer_optimizer=chemputeroptimizer,
        config=config.absolute().as_posix()
    )
