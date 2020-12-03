"""
Special constants related to analytical steps.
"""

from collections import OrderedDict


# Name of the solvent and corresponding maximum 1H signal ppm
# Ordered dictionary to preserve to priority order of the solvents
SHIMMING_SOLVENTS = OrderedDict({
    'DCM': 5.32,
    'CHCl3': 7.26,
    'acetonitrile': 1.94,
    'DMSO': 2.50,
    'methanol': 3.31,
    'H2O': 4.79,
})

SHIMMING_TIME_CHECK = 24*3600 # seconds
