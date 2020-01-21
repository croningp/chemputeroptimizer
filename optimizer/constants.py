# from xdl.steps import Add, HeatChill, HeatChillToTemp, Stir

SUPPORTED_STEPS = [
    'Add',
    'HeatChillToTemp',
    'HeatChill',
    'Stir',
]

SUPPORTED_PARAMETERS = {
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
