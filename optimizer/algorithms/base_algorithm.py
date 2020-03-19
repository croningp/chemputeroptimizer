"""Defines abstact algorithm class"""

from abc import ABC, abstractmethod


class AbstractAlgorithm(ABC):
    """Default constructor for algorithmic optimisation.
    
    Provides general methods to load parameters data, parse it into data arrays,
    sort the data according to the target value, map and validate the data against
    the experimental parameters, save the iteration for further access.

    Attributes:
        max_iterations (int): Maximum number of iterations.
    """
    def __init__(self):
        pass

    @abstractmethod
    def optimize(self, parameters, results, constraints=None):
        """Find the parameters for the next iteration.
        
        Uses the experimental matrixes to find new parameter set through
        given optimisation algorithm. Replaces the worst parameter with new points
        setting the target value to -1.
        This method has to be redefined in ancestor classes.

        Args:
            parameters (:obj: np.array): (n x i) size matrix where n is number of experiments and i
                is number of experimental parameters.
            results (:obj: np.array): (n x j) size matrix where j is number of the target parameters.
            constraints (Any): tuple with min/max values for the parameters
        
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

    def _check_termination(self):
        """Check if the optimal function value was found.
        
        Obtained either by meeting target criteria (from self.current_state['final_<parameter_name>']['target']),
        reaching maximum number of iterations or another way defined in the selected algorithm.
        This method has to be redefined in ancestor classes."""

    def save_iteration(self):
        """Save a parameter set with target function value."""

    def parse_constraints(self, constraints):
        """Parsing the setup constraints"""

        try:
            return tuple(constraints)

        except TypeError:
            pass
