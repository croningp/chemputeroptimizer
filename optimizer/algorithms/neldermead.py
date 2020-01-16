from ..algorithms import AbstractAlgorithm

class ModifiedNelderMead(AbstractAlgorithm):
    """The Nelder-Mead simplex optimization algorithm."""

    def initialise(self):
        pass

    def optmize(self):
        pass

    def _check_termination(self):
        if super()._check_termination():
            return super()._check_termination()

        else:
            return False
