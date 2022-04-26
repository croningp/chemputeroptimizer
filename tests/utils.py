# pylint: disable-all

from pathlib import Path
import os
import logging
import shutil
import time

import ChemputerAPI
from chempiler import Chempiler
from chemputeroptimizer import ChemputerOptimizer, OptimizerPlatform
from AnalyticalLabware.devices import chemputer_devices
from xdl import XDL


ROOT = Path(__file__).parent
GENERIC_CHEMPILER_OUTPUT = ROOT.joinpath('chempiler')

def get_chempiler(graph_file: str) -> Chempiler:

    return Chempiler(
        experiment_code='chempiler',
        graph_file=graph_file,
        output_dir=GENERIC_CHEMPILER_OUTPUT,
        simulation=True,
        device_modules=[ChemputerAPI, chemputer_devices]
    )

def get_chemputer_optimizer(xdl_file: str, graph_file: str) -> ChemputerOptimizer:

    return ChemputerOptimizer(
        xdl_file,
        graph_file,
    )

def get_prepared_xdl(xdl_file: str, graph_file: str) -> XDL:

    xdl = XDL(xdl_file, platform=OptimizerPlatform)

    xdl.prepare_for_execution(
        graph_file=graph_file,
        interactive=False,
        device_modules=[ChemputerAPI, chemputer_devices]
    )

    return xdl

def generic_optimizer_test(
    chempiler: Chempiler,
    chemputer_optimizer: ChemputerOptimizer,
    config: str,
):

    chemputer_optimizer.prepare_for_optimization(config)
    chemputer_optimizer.optimize(chempiler)

def remove_chempiler_files():
    print('Removing chempiler files.')
    for path in ROOT.rglob('*'):
        if path.is_dir() and 'chempiler' in path.as_posix() or 'log_files' in path.as_posix():
            shutil.rmtree(path, ignore_errors=True)

def remove_chemputeroptimizer_files():
    print('Removing chemputeroptimizer files.')
    for path in ROOT.rglob('*'):
        if path.is_dir() and 'iteration' in path.as_posix():
            shutil.rmtree(path, ignore_errors=True)

        if 'design.csv' in path.as_posix():
            os.remove(path)

def remove_all_logs():
    # Listing all loggers
    for name, logger in logging.root.manager.loggerDict.items():
        # Listing all handlers
        for handler in logging.getLogger(name).handlers:
            # Probing for any FileHandler
            if isinstance(handler, logging.FileHandler):
                # Closing handler
                handler.close()
                # Removing from logger
                logger.removeHandler(handler)
                # And removing corresponding log file
                for _ in range(10):
                    try:
                        os.remove(handler.baseFilename)
                    except PermissionError:
                        # Waiting till file is unlocked
                        time.sleep(.1)
                    except FileNotFoundError:
                        break

def remove_xdlexes(xdl_path):
    """Removes all xdlexes found in path"""
    print('Removing xdlexes files.')
    for path in xdl_path.iterdir():
        if path.suffix == '.xdlexe':
            os.remove(path)
