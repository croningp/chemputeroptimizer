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
}

TARGET_PARAMETERS = [
    'final_yield',
    'final_conversion', 
    'final_purity',
]