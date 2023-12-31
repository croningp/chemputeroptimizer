"""
Dummy "algorithm" to output the parameters obtained elsewhere and stored as csv
file.
"""

import os
from csv import reader as csv_reader
from typing import Optional

import numpy

from .base_algorithm import AbstractAlgorithm

class FromCSV(AbstractAlgorithm):
    """Dummy algorithm suggesting next experimental setup as read from
    indicated .csv file.
    """

    DEFAULT_CONFIG = {
        # Defaults to parameters.csv in the current directory
        "csv_path": os.path.join('.', 'parameters.csv'),
    }

    def __init__(self, dimensions=None, config=None):
        self.name = 'fromcsv'
        super().__init__(dimensions, config)

        self.read_csv()

    def read_csv(self):
        """ Reads csv and stores the values as iterator. """
        try:
            with open(self.config['csv_path']) as csv_file:
                self._csv_lines = list(csv_reader(csv_file))
                self.logger.debug("Reading file %r", csv_file)
                self.params = iter(self._csv_lines)
        except FileNotFoundError:
            raise FileNotFoundError("CSV file containing parameters for csv \
reader ({}) not found!".format(self.config['csv_path'])) from None

        # Skipping header
        self.csv_header = next(self.params)
        self.logger.debug("Read header from csv file:\n%s", self.csv_header)

    def suggest(
            self,
            parameters: Optional[numpy.ndarray] = None,
            results: Optional[numpy.ndarray] = None,
            constraints: Optional[numpy.ndarray] = None,
            n_batches: int = -1,
            n_returns: int = 1,
    ) -> numpy.ndarray:

        try:
            points = []

            for _ in range(n_returns):
                points.append(next(self.params))
                self.logger.debug("Read from csv file:\n%s",
                                  points[-1])

            return numpy.array(points, dtype=float)

        except StopIteration:
            raise StopIteration("CSV file exhausted, load a new one, or switch \
the algorithm") from None
