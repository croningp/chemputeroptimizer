"""Random search"""

import random

from ..algorithms import AbstractAlgorithm

class Random_(AbstractAlgorithm):
    def __init__(self, max_iterations):
        super().__init__(max_iterations)

    def optimize(self):
        print("Current setup", self.current_setup)
        print("Constraints", self.setup_constraints)

    def initialise(self):
        pass

    def _check_termination(self):
        pass