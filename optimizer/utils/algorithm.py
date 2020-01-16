"""
Module for interfacing algorithms for optimisation.
"""

from ..algorithms import ModifiedNelderMead, SNOBFIT

class Algorithm():
    """General class to provide methods for parametric optimization.
    
    Arguments:
        method (str): Name of the chosen algorithm.
        max_iterations (int): Maximum number of iterations.
    """

    def __init__(self, method, max_iterations):

        if method == 'nelder-mead':
            self.algorithm = ModifiedNelderMead(max_iterations)
        
        elif method == 'SNOBFIT':
            self.algorithm = SNOBFIT(max_iterations)

    def optimize(self, data):
        """Finds the next parameters set based on the experimental data
        
        Args:
            data (Dict): An experimental data with final analysis assignment,
                obtained from FinalAnalysis step.
        """
        self.algorithm.load_input(data)
        return self.algorithm.optmize()
