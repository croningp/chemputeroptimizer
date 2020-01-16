from ..algorithms import AbstractAlgorithm

class SNOBFIT(AbstractAlgorithm):
    """The Stable Noisy Optimization by Branch and Fit algorithm."""
    
    def initialise(self):
        pass

    def optmize(self):
        pass

    def _check_termination(self):
        if super()._check_termination():
            return super()._check_termination()

        else:
            return False