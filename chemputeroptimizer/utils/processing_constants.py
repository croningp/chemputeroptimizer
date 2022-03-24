""" Default constants for processing the analytical data. """

### NMR

# Arguments for region detection on various NMR nuclei
# Chosen experimentally on 80 Mhz Spinsolve NMR
DEFAULT_NMR_REGIONS_DETECTION = {
    '19F': {
        'magnitude': False,
        'derivative': True,
        'smoothed': False,
        'd_merge': 0.001,
        'd_expand': 0.125,
    },
}

NOVELTY_REGIONS_ANALYSIS = {
    '19F': {
        'magnitude': False,
        'derivative': True,
        'smoothed': False,
        'd_merge': 0.1,
        'd_expand': 0.1,
    }
}

# Maximum distance to peak to region (in ppm)
TARGET_THRESHOLD_DISTANCE = 0.5

# Method for referencing the spectrum
DEFAULT_NMR_REFERENCING_METHOD = 'closest'
