"""
Parameter definitions for the noise engine.
Each parameter has a name, range, and default value.
"""

PARAMETERS = {
    'gravity': {
        'name': 'Gravity',
        'min': 0.0,
        'max': 1.0,
        'default': 0.5,
        'description': 'Gravitational pull strength'
    },
    'density': {
        'name': 'Density',
        'min': 0.0,
        'max': 1.0,
        'default': 0.5,
        'description': 'Particle/grain density'
    },
    'filter_cutoff': {
        'name': 'Filter Cutoff',
        'min': 0.0,
        'max': 1.0,
        'default': 0.7,
        'description': 'Filter cutoff frequency'
    },
    'amplitude': {
        'name': 'Amplitude',
        'min': 0.0,
        'max': 1.0,
        'default': 0.5,
        'description': 'Output amplitude'
    }
}
