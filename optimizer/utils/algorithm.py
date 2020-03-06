"""
Module for interfacing algorithms for optimisation.
"""

from ..algorithms import ModifiedNelderMead, SNOBFIT, Random_

class Algorithm():
    """General class to provide methods for parametric optimization.
    
    Arguments:
        method (str): Name of the chosen algorithm.
        max_iterations (int): Maximum number of iterations.
    """

    def __init__(self, method=None, max_iterations=1):

        if method == 'nelder-mead':
            self.algorithm = ModifiedNelderMead(max_iterations)
        
        elif method == 'SNOBFIT':
            self.algorithm = SNOBFIT(max_iterations)

        else:
            self.algorithm = Random_(max_iterations)

    def optimize(self, data, result):
        """Finds the next parameters set based on the experimental data
        
        Args:
            data (Dict): An experimental data setup 
            result (Dict): Results of the experiment obtained
                from FinalAnalysis step.
        """
        self.algorithm.load_input(data, result)
        return self.algorithm.optimize()
