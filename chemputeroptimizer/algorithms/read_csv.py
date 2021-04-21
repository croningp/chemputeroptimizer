"""
Dummy "algorithm" to output the parameters obtained elsewhere and stored as csv
file.
"""

import os
from csv import reader as csv_reader
from typing import Optional

import numpy

from .base_algorithm import AbstractAlgorithm
from ..utils.errors import ParameterError

class FromCSV(AbstractAlgorithm):

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
                self.params = iter(self._csv_lines)
        except FileNotFoundError:
            raise FileNotFoundError("CSV file containing parameters for csv \
reader ({}) not found!".format(self.config['csv_path'])) from None

        # Skipping header
        self.csv_header = next(self.params)

    def suggest(
            self,
            parameters: Optional[numpy.ndarray] = None,
            results: Optional[numpy.ndarray] = None,
            constraints: Optional[numpy.ndarray] = None,
            n_batches: int = -1,
            n_returns: int = 1,
    ) -> numpy.ndarray:
        try:
            # First line (header) already read, proceed
            return numpy.array(next(self.params), dtype='float', ndmin=2)
        except StopIteration:
            raise StopIteration("CSV file exhausted, load a new one, or switch \
the algorithm") from None
