# from xdl.steps import Add, HeatChill, HeatChillToTemp, Stir

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
    'pH',
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

TARGET_PARAMETERS = [
    'final_yield',
    'final_conversion',
    'final_purity',
    'final_parameter',
    'spectrum_peak-area_XXX', # peak X coordinate (XXX)
    'spectrum_integration-area_LLL..RRR', # area left (LLL) and right (RRR) border
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
}
