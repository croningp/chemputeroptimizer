# from xdl.steps import Add, HeatChill, HeatChillToTemp, Stir

SUPPORTED_STEPS_PARAMETERS = {
    'Add': {
        "volume",
        "mass",
        "time",
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
    }
}

SUPPORTED_ANALYTICAL_METHODS = [
    'HPLC',
    'Raman',
    'NMR',
    'pH',
    'interactive',
]

SUPPORTED_FINAL_ANALYSIS_STEPS = [
    'Dry',
    'Evaporate',
    'Filter',
    'Stir',
    'Wait',
    'HeatChill',
    'HeatChillToTemp',
]

ANALYTICAL_INSTRUMENTS = {
    'Raman': 'OceanOpticsRaman',
    'NMR': 'ChemputerNMR',
}

TARGET_PARAMETERS = [
    'final_yield',
    'final_conversion',
    'final_purity',
    'final_parameter',
    'spectrum_peak-area_XXX', # peak X coordinate (XXX)
    'spectrum_integration-area_LLL-RRR', # area left (LLL) and right (RRR) border
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
}
