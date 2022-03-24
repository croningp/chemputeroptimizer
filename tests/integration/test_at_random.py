"""
Test optimizer functionality for randomly selected analytical instruments
and configurations.

This test does not guarantee that *everything* works, but useful to check if
very basic functionality is still alive.
"""

# pylint: disable-all

from random import sample
from itertools import product
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
TESTS_TO_RUN = 20

# XDLs
XDLS = {
    'hplc': FILES.joinpath('xdl', 'hplc.xdl').absolute().as_posix(),
    'nmr': FILES.joinpath('xdl', 'nmr.xdl').absolute().as_posix(),
    'raman': FILES.joinpath('xdl', 'raman.xdl').absolute().as_posix(),
}

# Graphs
GRAPHS = {
    'hplc': FILES.joinpath('graph', 'hplc.json').absolute().as_posix(),
    'nmr': FILES.joinpath('graph', 'nmr.json').absolute().as_posix(),
    'raman': FILES.joinpath('graph', 'raman.json').absolute().as_posix(),
}

# Config directory
CONFIGS = FILES.joinpath('config')
configs = CONFIGS.iterdir()

TODAYS_RANDOM_SETUP = sample(list(product(
    ['hplc', 'nmr', 'raman'],
    [config.as_posix() for config in configs]
)), k=TESTS_TO_RUN)

@pytest.fixture(scope='module', )
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
@pytest.mark.parametrize('instrument, config', TODAYS_RANDOM_SETUP)
def test_optimizer(chempiler, chemputeroptimizer, instrument, config):
    # Instantiating
    chempiler = chempiler(GRAPHS[instrument])
    chemputeroptimizer = chemputeroptimizer(XDLS[instrument], GRAPHS[instrument])
    # Testing
    generic_optimizer_test(
        chempiler=chempiler,
        chemputer_optimizer=chemputeroptimizer,
        config=config
    )
