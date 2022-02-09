"""
Main dynamic step to run iterative reaction optimization.
"""

# Std lib
import logging
import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Callable, Optional, Dict, Any

# XDL and chemputerXDL
from xdl import XDL
from xdl.utils.copy import xdl_copy
from xdl.steps.base_steps import (
    AbstractDynamicStep,
    Step,
    AbstractAsyncStep,
)
from xdl.steps.special.callback import Callback
from chemputerxdl.scheduling.scheduling import get_schedule

# AnalyticalLabware
from AnalyticalLabware.devices import chemputer_devices
from AnalyticalLabware.analysis.base_spectrum import AbstractSpectrum

# Relative
from .utils import (
    forge_xdl_batches,
    get_reagent_flasks,
    get_waste_containers,
    extract_optimization_params,
)
from ...utils import (
    SpectraAnalyzer,
    AlgorithmAPI,
)
from ...utils.errors import NoDataError

# for saving iterations
DATE_FORMAT = "%d%m%y"


class OptimizeDynamicStep(AbstractDynamicStep):
    """Outer level wrapper for optimizing multiple parameters in an entire
    procedure.

    Args:
        original_xdl (:obj: XDL): Full XDL procedure to be optimized. Must contain
            some steps wrapped with OptimizeStep steps.
    """

    PROP_TYPES = {
        'original_xdl': XDL,
        'algorithm_class': AlgorithmAPI,
    }

    def __init__(
            self,
            original_xdl: XDL,
            algorithm_class: AlgorithmAPI,
            **kwargs
        ):
        super().__init__(locals())

        self.logger = logging.getLogger('optimizer.dynamic_step')

    def _extract_parameters(self) -> None:
        """Extract optimization parameters from original xdl procedure."""

        parameters: Dict[str, Dict[str, Dict[str, float]]] = {}

        # Appending parameters batchwise
        for batch_number in range(1, self.batch_size + 1):
            # Will be same for all batches, but updates later on
            parameters[f'batch {batch_number}'] = extract_optimization_params(
                self.original_xdl
            )

        self.parameters = parameters

    def _forge_batches(self) -> List[XDL]:
        """Forge XDL batches from a single xdl. If number of batches is more
        than 1 - additional parameters will be requested from algorithmAPI.

        Args:
            xdl (XDL): An original xdl file to take the parameters from.

        Returns:
            List[XDL]: List of xdl objects, which differ by their parameters
                for optimization.
        """

        # Special case, single batch -> no update needed
        if self.batch_size == 1:
            return [xdl_copy(self.original_xdl)]

        # Querying the parameters from the algorithm if more than one batch
        # self.parameters already split batchwise
        self.algorithm_class.load_data(self.parameters)

        new_setup = self.algorithm_class.get_next_setup(
            n_batches=self.batch_size - 1  # Another one - original procedure
        )

        # Updating parameters dictionary
        for batch_id, batch_setup in new_setup.items():
            # Batchwise!
            for step_id, param_value in batch_setup.items():
                self.parameters[batch_id][step_id].update(
                    current_value = param_value,
                )

        # Forging and returning the xdls list
        return forge_xdl_batches(self.original_xdl, self.parameters)

    def update_steps_parameters(self) -> None:
        """Updates the parameter template and corresponding procedure steps"""

        # Queyring new setup
        new_setup = self.algorithm_class.get_next_setup()

        # Updating self.parameters to the new setup
        for batch_id, batch_setup in new_setup.items():
            # Batchwise!
            for step_id, param_value in batch_setup.items():
                self.parameters[batch_id][step_id].update(
                    current_value = param_value,
                )

        self.logger.debug('New parameters from algorithm:\n %s',
                          dict(new_setup))

        # Forging xdl batch
        xdl_batches = forge_xdl_batches(
            xdl=self.original_xdl,
            parameters=self.parameters,
        )

        # Scheduling only optimization is running in more than 1 batch
        if len(xdl_batches) > 1:

            # Scheduling
            self._xdl_schedule = get_schedule(
                xdls=xdl_batches,
                graph=self._graph,
                device_modules=[chemputer_devices]
            )
            self.working_xdl = self._xdl_schedule.to_xdl()

        else:

            self.working_xdl = xdl_batches[0]

            # Preparing the xdl for execution
            self.working_xdl.prepare_for_execution(
                self.graph,
                interactive=False,
                device_modules=[chemputer_devices]
            )

            # Creating iterator only if working with single batch
            self._xdl_iter = iter(self.working_xdl.steps)

        self._update_analysis_steps()
        self._update_constrained_steps()

    def _update_state(self):
        """Updates state attribute when procedure is over"""

        self.state['iteration'] += self.batch_size
        self.state['updated'] = True

        # reset the cursor for the next iteration
        self._cursor = 0

    def _check_flasks_full(self, platform_controller):
        """Ensure solvent and reagents flasks are full for the next iteration"""

        flasks_reagents = get_reagent_flasks(
            platform_controller.graph.graph # MultiDiGraph inside ChemputerGraph
        )

        for flask in flasks_reagents:
            try:
                previous_volume = self._previous_volume[flask['name']]
                previous_use = previous_volume - flask['current_volume']
            except KeyError:
                previous_use = flask['max_volume'] - flask['current_volume']
            finally:
                self._previous_volume[flask['name']] = flask['current_volume']

            self.logger.info(
                'Used %.2f ml from %s, current volume is %.2f',
                previous_use,
                flask['name'],
                flask['current_volume']
            )

            previous_use *= 1.2 # 20% for extra safety
            if previous_use > flask['current_volume']:
                confirmation_msg = f'Please refill {flask["name"]} with \
{flask["chemical"]} to {flask["max_volume"]} ml and press Enter to continue.\n'
                # confirming
                input(confirmation_msg)
                # setting the new current volume
                flask['current_volume'] = flask['max_volume']
                self._previous_volume.pop(flask['name'], None)

    def _check_wastes_empty(self, platform_controller):
        """Ensure waste bottles are empty for the next iteration"""

        waste_containers = get_waste_containers(
            platform_controller.graph.graph # MultiDiGraph inside ChemputerGraph
        )

        for flask in waste_containers:
            try:
                previous_volume = self._previous_volume[flask['name']]
                previous_use = flask['current_volume'] - previous_volume
            except KeyError:
                previous_use = flask['current_volume']
            finally:
                self._previous_volume[flask['name']] = flask['current_volume']

            self.logger.info(
                'Filled %s with %.2f ml, current volume is %.2f',
                flask['name'],
                previous_use,
                flask['current_volume']
            )

            previous_use *= 1.2 # 20% for extra safety
            if previous_use > flask['max_volume'] - flask['current_volume']:
                confirmation_msg = f'Please empty {flask["name"]} and press \
Enter to continue\n'
                # confirming
                input(confirmation_msg)
                # setting the new current volume
                flask['current_volume'] = flask['max_volume']
                self._previous_volume.pop(flask['name'], None)

    def execute(self, platform_controller, logger=None, level=0):
        """Dirty hack to get the state of the chemputer from its graph"""

        self._platform_controller = platform_controller
        super().execute(platform_controller, logger, level)

    def get_simulation_steps(self):
        """Should return steps for the simulation.

        No need to call the method, since the simulate method is overwritten.
        """

    def simulate(
            self,
            platform_controller: Any,
            logger: logging.Logger = None,
            level: int = 0,
            step_indexes: List[int] = None,
    ):
        """Run the optimization routine in the simulation mode.

        Since the optimizer handles simulation mode correctly, including various
        analytical methods (via "simulated" spectrum) and interactive method for
        the final analysis, the method is overwritten from the parent .simulate.
        The current method just executes the on_continue steps sequence just as
        the normal execute method.
        """

        continue_block = self.on_continue()
        self.executor.prepare_block_for_execution(self.graph, continue_block)

        while continue_block:
            for step in continue_block:
                if isinstance(step, AbstractAsyncStep):
                    self.async_steps.append(step)
                self.executor.execute_step(
                    platform_controller,
                    step,
                    async_steps=self.async_steps,
                    step_indexes=[0]
                )

            continue_block = self.on_continue()
            self.executor.prepare_block_for_execution(
                self.graph,
                continue_block
            )

        # Kill all threads
        self._post_finish()

    def on_prepare_for_execution(self, graph):
        """Additional preparations before execution"""

        self.logger.debug('Preparing Optimize dynamic step for execution.')

        # Saving graph for future xdl updates
        self._graph = graph

        # Getting parameters from the *raw* xdl
        self._extract_parameters()

        # Forging the xdl batches
        xdl_batches = self._forge_batches()

        # Scheduling only optimization is running in more than 1 batch
        if len(xdl_batches) > 1:

            # Scheduling
            self._xdl_schedule = get_schedule(
                xdls=xdl_batches,
                graph=self._graph,
                device_modules=[chemputer_devices]
            )
            self.working_xdl = self._xdl_schedule.to_xdl()

        else:
            self.working_xdl = xdl_batches[0]

            # Preparing the xdl for execution
            self.working_xdl.prepare_for_execution(
                self.graph,
                interactive=False,
                device_modules=[chemputer_devices]
            )

            # Iterating over xdl to allow checkpoints
            # Only if working with single batch
            self._cursor = 0
            self._xdl_iter = iter(self.working_xdl.steps[self._cursor:])

        self._update_analysis_steps()

        self._update_constrained_steps()

        # Load necessary tools
        self._analyzer = SpectraAnalyzer(
            reference=self.reference,  # loaded from the config file
            data_path=Path(self.original_xdl._xdl_file).parent,
        )

        # Tracking of flask usage
        self._previous_volume = {}

        self.state = {
            'iteration': 1,
            'current_result': {
                # Current result per batch
                f'batch {i}': {key: -1 for key in self.target}
                for i in range(1, self.batch_size + 1)
            },
            'updated': True,
            'done': False,
        }

        # Path to store data in
        self.iterations_path = self._get_data_path()

        # Saving schedule if exists
        try:
            xdl_path = Path(self.original_xdl._xdl_file)
            schedule_fp = self.iterations_path.joinpath(
                xdl_path.stem + '_schedule.json'
            )
            self._xdl_schedule.save_json(
                file_path=schedule_fp
            )
        # Don't save schedule if it does not exist,
        # I.e. single batch
        except AttributeError:
            pass

    def load_optimization_config(self, **kwargs):
        """Update the optimization configuration if required"""
        for k, v in kwargs.items():
            self.__dict__[k] = v

    def _update_constrained_steps(self):
        """Updates the constrained steps"""
        constrained = None
        updated_value = None
        osteps = []

        # find constrained step
        for step in self.working_xdl.steps:
            if step.name == "ConstrainedStep":
                relevant_ids = step.ids
                constrained = step
                updated_value = constrained.target
            elif step.name == "OptimizeStep":
                osteps.append(step)

        if not constrained:
            return

        # find relevant optimize steps
        for step in osteps:
            if int(step.id) in relevant_ids:
                value = step.children[0].properties[constrained.parameter]
                updated_value -= value

        # update the constrained parameter
        constrained.children[0].properties[constrained.parameter] = updated_value

    def _update_analysis_steps(self):
        """Updates the analysis steps"""

        analysis_method = None

        def assign_callback(step: Step) -> None:
            """Recursive function to traverse down the steps and assign given
            callback to the found FinalAnalysis or Analyze step."""

            if step.name == 'FinalAnalysis' or step.name == 'Analyze':
                nonlocal analysis_method
                analysis_method = step.method
                if analysis_method == 'interactive':
                    step.on_finish = self.interactive_final_analysis_callback
                    return
                step.on_finish = self.on_final_analysis
                return

            # Adding necessary callbacks for the monitoring step
            if step.name == 'StartMonitoring':
                step.on_going = self._on_monitoring_update
                step.on_finish = self._on_monitoring_finish

            for substep in step.steps:
                assign_callback(substep)

        for step in self.working_xdl.steps:
            assign_callback(step)
            # Adding necessary callbacks for the monitoring step
            if step.name == 'StartMonitoring':
                step.on_going = self._on_monitoring_update
                step.on_finish = self._on_monitoring_finish

        if analysis_method is None:
            self.logger.info('No analysis steps found!')
            return

        if analysis_method == 'interactive':
            self.logger.info('Running with interactive FinalAnalysis method')
            return

    def _on_monitoring_update(self, spectrum: AbstractSpectrum) -> None:
        """Callback function to update the spectrum during monitoring.

        Args:
            spectrum (:obj:AbstractSpectrum): Instance from spectrum class,
                containing all spectral information.
        """

        self._analyzer.load_spectrum(spectrum=spectrum)

    def _on_monitoring_finish(self) -> None:
        """Callback function called when the monitoring is stopped.

        Do nothing for now.
        """

    def _on_monitoring_update(self, spectrum: AbstractSpectrum) -> None:
        """Callback function to update the spectrum during monitoring.

        Args:
            spectrum (:obj:AbstractSpectrum): Instance from spectrum class,
                containing all spectral information.
        """

        self._analyzer.load_spectrum(spectrum=spectrum)

    def _on_monitoring_finish(self) -> None:
        """Callback function called when the monitoring is stopped.

        Do nothing for now.
        """

    def _get_blank_spectrum(self, graph, method):
        """Step to measure blank spectrum"""

    def interactive_final_analysis_callback(
        self, batch_id: Optional[str]) -> Callable[[AbstractSpectrum], None]:
        """Callback function to prompt user input for final analysis"""

        if batch_id is None:
            batch_id = 'batch 1'

        def interactive_update(spectrum: AbstractSpectrum = None) -> None:

            msg = 'You are running FinalAnalysis step interactively.\n'
            msg += 'Current batch is "{}"\n'.format(batch_id)
            msg += f'Current procedure is running towards >{self.target}< parameters.\n'
            msg += 'Please type the result of the analysis below\n'
            msg += '***as <target_parameter>: <current_value>***\n'

            while True:
                answer = input(msg)
                pattern = r'.*:.*'
                match = re.fullmatch(pattern, answer)
                if not match:
                    warning_msg = '\n### Please type "PARAMETER NAME": PARAMETER \
    VALUE ###\n'
                    self.logger.warning(warning_msg)
                    continue
                param, param_value = match[0].split(':')

                try:
                    self.logger.info('Last value for %s is %.02f, updating.',
                                    param, self.state['current_result'][batch_id][param])
                    self.state['current_result'][batch_id][param] = float(param_value)
                except KeyError:
                    key_error_msg = f'{param} is not valid target parameter\n'
                    key_error_msg += 'try one of the following:\n'
                    key_error_msg += '>>>' + '  '.join(self.target.keys()) + '\n'
                    self.logger.warning(key_error_msg)
                except ValueError:
                    self.logger.warning('Value must be float!')
                else:
                    break

            # saving
            self.save_batch(batch_id)

            self.state['updated'] = False

        return interactive_update

    def on_final_analysis(
        self,
        batch_id: Optional[str] = None
    ) -> Callable[[AbstractSpectrum], None]:
        """Factory for callback update functions.

        Creates callback function for when spectra has been recorded at end of
        procedure. Updates the state (current result) parameter for the given
        batch id.

        Args:
            batch_id (str): Batch id to assign the result to.
        """

        if batch_id is None:
            batch_id = 'batch 1'

        def update_result(spectrum: AbstractSpectrum) -> None:
            """Closure function to update the result for a given batch id.

            Args:
                spectrum (:obj:AbstractSpectrum): Spectrum object, contaning
                    methods for performing basic processing and analysis.
            """

            self._analyzer.load_spectrum(spectrum)

            # Final parsing occurs in SpectraAnalyzer.final_analysis
            result = self._analyzer.final_analysis(
                self.reference,
                self.target,
                self.constraints
            )

            # Updating state
            self.state['current_result'][batch_id] = result

            # Saving
            self.save_batch(batch_id, spectrum)

            # Setting the updated tag to false, to update the
            # procedure when finished
            self.state['updated'] = False

            # Special case - analyze the control experiment
            if self.algorithm_class.control:
                # Calculate special control result
                control_result = self._analyzer.control_analysis(
                    spectrum,
                    self.algorithm_class.control_experiment_idx[batch_id]
                )
                # Save it
                self.state['control_result'] = control_result
                # Remove control spectrum from the list of spectra
                # This is mainly done to preserve the pipeline of the
                # Novelty exploration, where the spectra are compared
                self._analyzer.spectra.pop()

        return update_result

    def _check_control(self) -> bool:
        """Check the results of the control experiment.

        The validation is based on the result returned after spectra comparison
        in the SpectraAnalyzer class. Any additional comparison logic should
        be written there. This method is a utility method to validate the
        result of the control experiment and decide, whether the optimization
        is worth proceeding.

        Does nothing for now.
        """

        #TODO
        return True

    def _check_termination(self):

        self.logger.info(
            'Finished iteration %d.\nLast parameters: %s\nLast results: %s\n',
            self.state['iteration'] - 1,
            self.parameters,
            self.state['current_result'])

        if self.state['iteration'] > self.max_iterations:
            self.logger.info('Max iterations reached. Done.')
            return True

        results = []

        for batch_id, batch_result in self.state['current_result'].items():

            batch_results = []

            # Results per batch
            for target_parameter in self.target:
                self.logger.info(
                    'Target parameter (%s) for %s is %.02f',
                    target_parameter,
                    batch_id,
                    batch_result[target_parameter]
                )

                batch_results.append(
                    float(batch_result[target_parameter]) >
                    float(self.target[target_parameter])
                )

            # True only if all results gave true for the batch
            results.append(all(batch_results))

        # Returns True if any of the batches met all target parameters
        return any(results)

    def on_start(self):

        self.logger.info('Optimize Dynamic step starting')

        return []

    def on_continue(self):

        try:
            next_step = next(self._xdl_iter)
            self._cursor += 1
            return [next_step]

        except StopIteration:
            # Procedure is over, checking and restarting

            self._check_flasks_full(self._platform_controller)
            self._check_wastes_empty(self._platform_controller)

            # All necessary updates wrapped in single method
            self.on_iteration_complete()

            if self._check_termination():
                return []

            return self.on_continue()

        # Happens if xdl iterator is not set, when working with several batches
        except AttributeError:

            # If optimization is over
            if self._check_termination():
                return []

            steps = self.working_xdl.steps

            # Appending special callback step to update the state after
            # All batches within iteration are complete
            steps.append(Callback(
                self.on_iteration_complete,
            ))

            return steps

    def on_iteration_complete(self):
        """Special callback function to update the ODS state at the end of
        single iteration.
        """

        if not self.state['updated']:
            # Loading results into algorithmAPI
            self.algorithm_class.load_data(
                self.parameters,
                self.state['current_result']
            )
            # Saving
            self.save()

            if not self._check_control():
                # Do something if the control experiment result is not
                # Satisfying
                #TODO: additional logic here if needed
                pass

            # Updating xdls for the next round of iterations
            self.update_steps_parameters()
            self._update_state()

        # Reset async steps
        # This is very important to prevent accumulating async steps from
        # Previous iterations
        self.async_steps = []

    def on_finish(self):
        return []

    def resume(self, platform_controller, logger=None, level=0):
        # straight to on_continue
        self.started = False
        self.start_block = []

        # creating new iterator from last cursor position
        self._cursor -= 1
        self._xdl_iter = iter(self.working_xdl.steps[self._cursor:])
        self.execute(platform_controller, logger=logger, level=level)

    def cleaning_steps(self):
        pass

    def save(self):
        """Saves the data for the current iteration"""

        # Updating path for saving data
        self.iterations_path = self._get_data_path()
        xdl_path = Path(self.original_xdl._xdl_file)

        # Saving algorithmic data
        try:
            alg_file = self.iterations_path.joinpath(
                xdl_path.stem + '_data.csv',
            )
            self.algorithm_class.save(alg_file)
        except NoDataError:
            pass

        # Saving schedule if exists
        try:

            schedule_fp = self.iterations_path.joinpath(
                xdl_path.stem + '_schedule.json'
            )
            self._xdl_schedule.save_json(
                file_path=schedule_fp
            )
        # Don't save schedule if it does not exist,
        # I.e. single batch
        except AttributeError:
            pass

    def save_batch(self, batch_id: str, spec: AbstractSpectrum = None) -> None:
        """Save individual batch data.

        Args:
            batch_id (str): Individual batch id to store the data from.
            spec (AbstractSpectrum): Optionally, save spectrum with batch data.
        """

        # Updating path for saving data
        self.iterations_path = self._get_data_path()
        xdl_path = Path(self.original_xdl._xdl_file)
        batch_dir = '{}{}'.format(
            batch_id,
            ' control' if self.algorithm_class.control else ''
        )
        batch_path = self.iterations_path.joinpath(batch_dir)
        batch_path.mkdir(parents=True, exist_ok=True)

        # Forging batch data
        batch_data: Dict[str, Dict[str, float]] = {}
        batch_data.update(self.parameters[batch_id])
        batch_data.update(self.state['current_result'][batch_id])

        # Saving
        batch_file_path = batch_path.joinpath(
            xdl_path.stem + '_params.json'
        )

        with open(batch_file_path, 'w') as fobj:
            json.dump(batch_data, fobj, indent=4)

        self.logger.info('Parameters for %s is saved to %s', batch_id,
                         batch_file_path.absolute())

        # Saving xdl
        working_xdl_path = batch_path.joinpath(
            xdl_path.stem + f'_{self.state["iteration"]}.xdl'
        )
        self.working_xdl.save(working_xdl_path)

        self.logger.info('XDL for %s is saved to %s', batch_id,
                         batch_file_path.absolute())

        if spec:
            # Hack to save spectrum in proper folder
            spec.path = batch_path
            spec.save_data()

    def _get_data_path(self) -> Path:
        """Get the data path to save the results to.

        If platform controller is initialized, the root is set to the
        experiment name, otherwise to parent directory of the xdl file.
        """

        today = datetime.today().strftime(DATE_FORMAT)

        try:
            root = Path(self._platform_controller.exp_name).absolute()
        except AttributeError:
            # If controller is not initialize - set root to the xdl file
            # Parent directory
            root = Path(self.original_xdl._xdl_file).absolute().parent

        # Path to store data iteration-wise
        iterations_path = root.joinpath(
            f'iterations_{today}',
            str(self.state['iteration'])
        )
        iterations_path.mkdir(parents=True, exist_ok=True)

        return iterations_path
