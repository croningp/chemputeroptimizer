"""Running tests on all possible configurations and analytical instruments."""

# pylint: disable-all

from pathlib import Path

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

# XDLs
HPLC_XDL = FILES.joinpath('xdl', 'hplc.xdl').absolute().as_posix()
NMR_XDL = FILES.joinpath('xdl', 'nmr.xdl').absolute().as_posix()
RAMAN_XDL = FILES.joinpath('xdl', 'raman.xdl').absolute().as_posix()

# Graphs
HPLC_GRAPH = FILES.joinpath('graph', 'hplc.json').absolute().as_posix()
NMR_GRAPH = FILES.joinpath('graph', 'nmr.json').absolute().as_posix()
RAMAN_GRAPH = FILES.joinpath('graph', 'raman.json').absolute().as_posix()

# Config directory
CONFIGS = FILES.joinpath('config')
config_files = [config.as_posix() for config in CONFIGS.iterdir()]

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
        config=config
    )

@pytest.mark.integration
@pytest.mark.parametrize('config', config_files[:])
def test_hplc_optimizer(chempiler, chemputeroptimizer, config):
    # Instantiating
    chempiler = chempiler(HPLC_GRAPH)
    chemputeroptimizer = chemputeroptimizer(HPLC_XDL, HPLC_GRAPH)
    # Testing
    generic_optimizer_test(
        chempiler=chempiler,
        chemputer_optimizer=chemputeroptimizer,
        config=config
    )

@pytest.mark.integration
@pytest.mark.parametrize('config', config_files[:])
def test_raman_optimizer(chempiler, chemputeroptimizer, config):
    # Instantiating
    chempiler = chempiler(RAMAN_GRAPH)
    chemputeroptimizer = chemputeroptimizer(RAMAN_XDL, RAMAN_GRAPH)
    # Testing
    generic_optimizer_test(
        chempiler=chempiler,
        chemputer_optimizer=chemputeroptimizer,
        config=config
    )
