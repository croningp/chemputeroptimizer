"""Module contains all necessary constants for the ChemputerOptimizer."""

SUPPORTED_STEPS_PARAMETERS = {
    'Add': {
        "volume",
        "time",
        "dispense_speed",
    },
    'AddSolid': {
        "mass",
    },
    'HeatChill': {
        "time",
        "temp",
    },
    'HeatChillToTemp': {
        "temp",
    },
    'Stir': {
        "time",
    },
    'Wait': {
        "time",
    }
}

SUPPORTED_ANALYTICAL_METHODS = [
    'HPLC',
    'Raman',
    'NMR',
    # 'pH',
    'interactive',
]

SUPPORTED_FINAL_ANALYSIS_STEPS = [
    # 'Dry',
    # 'Evaporate',
    # 'Filter',
    'Stir',
    'Wait',
    'HeatChill',
    'HeatChillToTemp',
]

ANALYTICAL_INSTRUMENTS = {
    'Raman': 'OceanOpticsRaman',
    'NMR': 'ChemputerNMR',
    'HPLC': 'HPLCController',
    'IDEX': 'IDEXMXIIValve'
}

# Spectra objects that have special methods for analysis
# And calculation of the corresponding loss function
SUPPORTED_SPECTRA_FOR_ANALYSIS = [
    'spinsolvenmrspectrum',
    'ramanspectrum',
    'agilenthplcchromatogram',
]

TARGET_PARAMETERS = [
    # 'final_yield',
    # 'final_conversion',
    # 'final_purity',
    # 'final_parameter',
    'spectrum_peak_area_XXX', # peak X coordinate (XXX)
    'spectrum_integration_area_LLL..RRR', # area left (LLL) and right (RRR) border
    'novelty', # e.g. number of new peaks on the product spectrum
]

DEFAULT_OPTIMIZATION_PARAMETERS = {
    'max_iterations': 1,
    'target': {
        'final_parameter': 1,
        },
    'algorithm': {
        'name': 'random',
        },
    'reference': None,
    'batch_size': 1,
    'constraints': None,
    'control': {
        'n_runs': 1,
        'every': 5
    }
}

# If no parameters for the OptimizeStep are given,
# Using this as a range from the default setting
DEFAULT_OPTIMIZE_STEP_PARAMETER_RANGE = (0.8, 1.2)  # plus-minus 20%

# Special variables names
NOVELTY = 'novelty_'  # "_" is added for the correct parsing
TARGET = 'target'
BATCH_1 = 'batch 1'
CURRENT_VALUE = 'current_value'
MIN_VALUE = 'min_value'
MAX_VALUE = 'max_value'
ALGORITHM = 'algorithm'
