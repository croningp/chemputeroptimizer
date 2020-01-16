from abc import ABC, abstractmethod
from collections import OrderedDict

class AbstractAlgorithm(ABC):
    """Default constructor for algorithmic optimisation.
    
    Provides general methods to load parameters data, parse it into data arrays,
    sort the data according to the target value, map and validate the data against
    the experimental parameters, save the iteration for further access.

    Attributes:
        max_iterations (int): Maximum number of iterations.
    """

    def __init__(self, max_iterations):

        self.max_iterations = max_iterations

        self.current_setup = None
        self.parameter_matrix = None
        self.result_matrix = None
        self.full_experiment_matrix = None

    def load_input(self, data):
        """Loads the data dictionary and updates self.current_setup.
        
        Args:
            data (dict): Nested dictionary containing all input parameters
                and current value of the target function.

        Example:
            {
                "HeatChill1_temp": {
                    "value": 35,
                    "max": 70,
                    "min": 25,
                },
                "final_yield": {
                    "value": 0.75,
                    "target": 0.95,
                }
            }
        """

        self.current_setup = OrderedDict(data)

    def _parse_data(self):
        """Parse the experimental data.
        
        Create the following arrays for the first experiment and add the subsequent data as rows:
            self.parameter_matrix: (n x i) size matrix where n is number of experiments and i
                is number of experimental parameters;
            self.result_matrix: (n x j) size matrix where j is number of the target parameters;
            self.full_experiment_matrix: (n x i+j) size matrix.
        
        Example:
            The experimental result:
                {
                    "Add1_volume": {
                        "value": 1.5,
                        "min": 1,
                        "max": 2,
                    }
                    "HeatChill1_temp": {
                        "value": 35,
                        "max": 70,
                        "min": 25,
                    },
                    "final_yield": {
                        "value": 0.75,
                        "target": 0.95,
                    }
                }
            will be dumped into the following np.arrays matrixes:
                self.parameter_matrix = np.array([1.5, 35.]);
                self.result_matrix = np.array([0.75]);
                self.full_experiment_matrix = np.array([1.5, 35., 0.75]).
        """

    def _sort(self):
        """Sorts the experimental matrixes according to target value."""

    def _map_data(self):
        """Maps the data with the parameters."""

    @abstractmethod
    def optmize(self):
        """Find the parameters for the next iteration.
        
        Uses the experimental matrixes to find new parameter set through
        given optimisation algorithm. Replaces the worst parameter with new points
        setting the target value to -1.
        This method has to be redefined in ancestor classes.
        
        Returns:
            (np.array): An array with new set of experimental input parameters.
        """

    @abstractmethod
    def initialise(self):
        """Get the initial setup parameters to run the optimisation.
        
        Check if enough data points available to perform the optimisation according to
        the chosen algorithm. If not - get the initial random setup to a given parameter
        space.
        This method has to be redefined in ancestor classes.
        """

    def _validate_parameters(self, parameters):
        """Validate parameters against the given min-max range.
        
        Map given parameters to the initial experimental dictionary and check
        against provided min/max values.

        Args:
            parameters (np.array): An array with experimental input parameters.
            
        Returns:
            (np.array): An array with boolean values, mapped to experimental input parameters.
        """

    @abstractmethod
    def _check_termination(self):
        """Check if the optimal function value was found.
        
        Obtained either by meeting target criteria (from self.current_state['final_<parameter_name>']['target']),
        reaching maximum number of iterations or another way defined in the selected algorithm.
        This method has to be redefined in ancestor classes."""

    def save_iteration(self):
        """Save a parameter set with target function value."""
