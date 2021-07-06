"""
Asynchronous step to monitor the reaction progress using specified analytical
method.
"""

# std lib
import time
import logging
from typing import Callable, List, Any

# external
from networkx import MultiDiGraph
from AnalyticalLabware.analysis.base_spectrum import AbstractSpectrum

# XDL
from xdl.steps.base_steps import AbstractBaseStep, AbstractAsyncStep, Step
from xdl.errors import XDLError

from chemputerxdl.steps.base_step import ChemputerStep

# Relative
from .steps_analysis import RunRaman
from .utils import find_instrument

# Constants
SUPPORTED_METHODS = ['raman']


class StartMonitoring(ChemputerStep, AbstractAsyncStep):
    """Start monitoring using the specified analytical method.

    Args:
        pid (str): Process name, used to correctly stop it.
        method (str): Name of the analytical method. Currently only Raman is
            supported, as no sampling needed.
        analysis_delay (float): Delay between spectra recording. DEfaults to 10
            seconds.
        on_going (Optional, Callable): Callback function executed when new
            spectrum is recorded.
        on_finish (Optional, Callable): Callback function executed when the
            monitoring is finished.
    """

    PROP_TYPES = {
        'pid': str,
        'method': str,
        'analysis_delay': float,
        'on_going': Callable[[AbstractSpectrum], None],
        'on_finish': Callable,
    }

    INTERNAL_PROPS = [
        'instrument',
        'starting_time',
    ]

    DEFAULT_PROPS = {
        'analysis_delay': 10,
    }

    def __init__(
        self,
        pid: str,
        method: str,
        analysis_delay: float,
        on_going: Callable[[AbstractSpectrum], None] = None,
        on_finish: Callable = None,
        **kwargs
    ) -> None:
        super().__init__(locals())

        if self.method not in SUPPORTED_METHODS:
            raise NotImplementedError(
                f'Only {SUPPORTED_METHODS} are supported!')

        self._should_end: bool = False
        self.finished: bool = False
        self.exception: Exception = None

    def on_prepare_for_execution(self, graph: MultiDiGraph) -> None:
        """Necessary preparation for step execution."""

        self.instrument = find_instrument(graph, self.method)

    def async_execute(
        self,
        platform_controller: Any,
        logger: logging.Logger = None,
        level: int = 0,
        step_indexes: List[int] = None,
    ) -> bool:
        """Run the analytical steps in infinite loop until the process is
        stopped.
        """

        analysis_steps = [
            RunRaman(
                raman=self.instrument,
                on_finish=self.on_going,
                blank=False,
            )
        ]

        # Run the analysis until the thread is killed
        while not self._should_end:
            try:
                for step in analysis_steps:
                    step.execute(platform_controller)

                logger.debug(
                    'Background analysis finished, waiting for %.2f seconds',
                    self.analysis_delay
                )
                # Using time.sleep here to avoid numerous logging massages
                # In the Wait step
                time.sleep(self.analysis_delay)

            except XDLError as err:
                logger.exception(
                    'Exception while running background analysis.')
                # Breaking the loop in case of error
                self.finished = True
                # Saving exception info to raise later
                self.exception = err
                break

        if self.on_finish is not None:
            self.on_finish()

        return True

class StopMonitoring(ChemputerStep, AbstractBaseStep):
    """Utility step to stop the background monitoring step.

    Args:
        pid (str): Name of the monitoring process to stop.
    """

    PROP_TYPES = {
        'pid': str,
    }

    def __init__(self, pid: str, **kwargs) -> None:

        super().__init__(locals())
        self.steps = []

    def execute(
        self,
        async_steps: List[AbstractAsyncStep],
        logger: logging.Logger = None,
        level: int = 0,
        step_indexes: List[int] = None,
    ) -> None:

        # Killing the async step
        for async_step in async_steps:
            if async_step.pid == self.pid:
                # Killing process
                async_step.kill()
                # Waiting for the thread
                async_step.thread.join()
                # If any exceptions occurred - raise?

                if (hasattr(async_step, 'exception')
                        and async_step.exception is not None):

                    # TODO decide on the exception handling
                    logger.exception(
                        "Exception in %s background monitoring step:\n%s",
                        async_step,
                        async_step.exception
                    )

    def locks(self, chempiler):
        """No locks for this step."""
        return [], [], []
