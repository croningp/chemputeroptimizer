"""
Wrapper for pyDOE2.
"""

import os
from typing import Optional

import pyDOE2
import pandas as pd
import numpy as np

from .base_algorithm import AbstractAlgorithm


DESIGNS = {
    "fullfact": pyDOE2.fullfact,
    "fracfact": pyDOE2.fracfact,
    "fracfact_by_res": pyDOE2.fracfact_by_res,
    "bbdesign": pyDOE2.bbdesign,
    "ccdesign": pyDOE2.ccdesign,
    "pbdesign": pyDOE2.pbdesign,
    "lhs": pyDOE2.lhs,
    "gsd": pyDOE2.gsd
}


class DOE(AbstractAlgorithm):
    """"
    Experimental Designs as provided by the pyDOE2 package.
    Once a design is exhausted, user intervention is required for further
    optimization. For usage, see: https://pythonhosted.org/pyDOE/
    """

    DEFAULT_CONFIG = {
        # always needed
        "design": "fullfact",  # which design to use
        "levels": 2,  # int or List for mixed level designs
        "center": 1,  # number of center points to be added
        "star": False,  # if star points are to be added
        # design specific options
        "resolution": 4,  # only used by fracfact_by_res
        "generator_string": "a b -ab",  # only used by fractfact
        "alpha": "o",  # only used for ccdesigns
        "face": "cci",  # only used for ccdesigns
        "reduction": 3,  # only used for gsd
        "samples": 100,  # only used for lhs
        "criterion": "center",  # only used for lhs
        # for reproducibility
        "shuffle": True,  # randomize order
        "seed": 42,  # for reproducibility
        "csv_path": os.path.join('.', 'design.csv'),  # for saving the design
    }

    def __init__(self, dimensions=None, config=None):
        self.name = 'DOE'
        super().__init__(dimensions, config)
        self.params = None
        self.n_factors = len(dimensions)
        self.rng = np.random.default_rng(self.config["seed"])

        if isinstance(self.config["levels"], int):
            self.levels = [self.config["levels"] for _ in range(self.n_factors)]
        else:
            self.levels = self.config["levels"]

        self.initialize()

    def initialize(self):
        """Create the design matrix and parameter iterator."""
        doe_func = DESIGNS[self.config["design"]]
        args = self.get_args()
        design = doe_func(*args)

        if self.config["design"] not in ["fullfact", "lhs", "gsd"]:
            design = self.convert_zero_centered(design)

        if self.config["star"]:
            design = self.add_star_points(design)

        if self.config["center"] > 0:
            repeats = self.config["center"]
            design = self.add_center_points(design, repeats)

        # self.design_to_csv(design, fname="DOE_raw")

        if self.config["shuffle"]:
            self.rng.shuffle(design)  # in-place

        design = self.decode_vars(design)
        self.design_to_csv(design)
        self.params = iter(design)

    def get_args(self):
        """Get a tuple with arguments depending on the chosen design."""
        if self.config["design"] == "fullfact":
            args = (np.array(self.levels),)
        elif self.config["design"] == "fracfact_by_res":
            args = (self.n_factors, self.config["resolution"])
        elif self.config["design"] == "fracfact":
            args = (self.config["generator_string"],)
        elif self.config["design"] == "bbdesign":
            # 0 center points, added later
            args = (self.n_factors, 0)
        elif self.config["design"] == "ccdesign":
            # 0 center points, added later
            args = (self.n_factors, (0, 0), self.config["alpha"],
                    self.config["face"])
        elif self.config["design"] == "lhs":
            args = (self.n_factors, self.config["samples"],
                    self.config["criterion"])
        elif self.config["design"] == "gsd":
            args = (self.levels, self.config["reduction"])
        else:
            args = (self.n_factors,)
        return args

    def add_center_points(self, design, repeats):
        """Method to add center points. Do not use in >2-level designs."""
        center_points = pyDOE2.doe_repeat_center.repeat_center(
            self.n_factors, repeats)
        center_points = self.convert_zero_centered(center_points)
        return pyDOE2.doe_union.union(center_points, design)

    def add_star_points(self, design, alpha='faced', center=(1, 1)):
        """Method to add star points. Non-default values for alpha,
        will violate the constraints. Do not use in >2-level designs."""
        star_points, _ = pyDOE2.doe_star.star(self.n_factors,
            alpha=alpha, center=center)
        star_points = self.convert_zero_centered(star_points)
        return pyDOE2.doe_union.union(design, star_points)

    def convert_zero_centered(self, design):
        "Converts design matrices with bounds [-1, 1] to bounds [0, 1]."
        return (design + 1) / 2

    def decode_vars(self, design):
        """Maps coded variables in design matrix onto actual search space."""
        decoded = np.empty_like(design)

        # n_rows, n_cols = design.shape
        for idx, bounds in enumerate(self.dimensions):
            low, high = bounds
            increment = (high - low) / (self.levels[idx]-1)
            decoded[:, idx] = increment * design[:, idx] + low
        return np.round(decoded, 3)

    def design_to_csv(self, design, fname=None, names=None):
        """Writes design into csv file."""
        df = pd.DataFrame(design, columns=names)
        if fname is None:
            fname = self.config["csv_path"]
        else:
            fname += ".csv"
        return df.to_csv(fname, index=False)

    def suggest(
            self,
            parameters: Optional[np.ndarray] = None,
            results: Optional[np.ndarray] = None,
            constraints: Optional[np.ndarray] = None,
            n_batches: int = -1,
            n_returns: int = 1,
    ) -> np.ndarray:
        """Returns the next points from the design matrix.
        When using parallelisation, the number of runs should be a multiple
        of the batch_size. Otherwise, some experiments may not be carried out.
        """
        try:
            points = np.empty((0, self.n_factors))
            for _ in range(n_returns):
                next_ = next(self.params)
                points = np.vstack((points, next_))
            return points

        except StopIteration:
            raise StopIteration("Experimental Design exhausted, "
                    "load a new one, or switch the algorithm") from None
