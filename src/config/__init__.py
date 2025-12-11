"""
Central Configuration
All constants, mappings, and settings in one place
"""

import math
import json
import os

# === GENERATOR PARAMETERS ===
# Single source of truth for STANDARD generator parameters (shared by all)
# Order determines UI slider order
GENERATOR_PARAMS = [
    {
        'key': 'frequency',
        'label': 'FRQ',
        'tooltip': 'Frequency / Rate',
        'default': 0.5,
        'min': 0.5,
        'max': 80.0,
        'curve': 'exp',
        'unit': 'Hz',
        'invert': False,
    },
    {
        'key': 'cutoff',
        'label': 'CUT',
        'tooltip': 'Filter Cutoff',
        'default': 0.5,
        'min': 80.0,
        'max': 16000.0,
        'curve': 'exp',
        'unit': 'Hz',
        'invert': False,
    },
    {
        'key': 'resonance',
        'label': 'RES',
        'tooltip': 'Filter Resonance',
        'default': 0.5,
        'min': 0.1,
        'max': 1.0,
        'curve': 'lin',
        'unit': '',
        'invert': True,  # High slider = low rq = more resonance
    },
    {
        'key': 'attack',
        'label': 'ATK',
        'tooltip': 'VCA Attack',
        'default': 0.5,
        'min': 0.001,
        'max': 0.5,
        'curve': 'exp',
        'unit': 's',
        'invert': False,
    },
    {
        'key': 'decay',
        'label': 'DEC',
        'tooltip': 'VCA Decay',
        'default': 0.5,
        'min': 0.01,
        'max': 2.0,
        'curve': 'exp',
        'unit': 's',
        'invert': False,
    },
]


def map_value(normalized, param):
    """
    Map normalized 0-1 slider value to real parameter value.
    Handles linear/exponential curves and inversion.
    """
    if param.get('invert', False):
        normalized = 1.0 - normalized
    
    min_val = param['min']
    max_val = param['max']
    
    if param.get('curve', 'lin') == 'exp':
        # Exponential mapping (need non-zero min)
        if min_val <= 0:
            min_val = 0.001  # Prevent division by zero
        return min_val * math.pow(max_val / min_val, normalized)
    else:
        # Linear mapping
        return min_val + (max_val - min_val) * normalized


def format_value(value, param):
    """
    Format a real value with its unit for display.
    """
    unit = param.get('unit', '')
    
    if unit == 'Hz':
        if value >= 1000:
            return f"{value/1000:.1f}kHz"
        else:
            return f"{value:.0f}Hz"
    elif unit == 's':
        if value < 0.01:
            return f"{value*1000:.1f}ms"
        elif value < 1.0:
            return f"{value*1000:.0f}ms"
        else:
            return f"{value:.2f}s"
    elif unit == '':
        return f"{value:.2f}"
    else:
        return f"{value:.2f}{unit}"


# === CLOCK ===
CLOCK_RATES = ["x8", "x4", "x2", "CLK", "/2", "/4", "/8", "/16"]
CLOCK_DEFAULT_INDEX = 3  # CLK

# Rate name -> SuperCollider index
CLOCK_RATE_INDEX = {
    "x8": 0,   # 32nd notes
    "x4": 1,   # 16th notes
    "x2": 2,   # 8th notes
    "CLK": 3,  # Quarter notes
    "/2": 4,   # Half notes
    "/4": 5,   # Whole notes
    "/8": 6,   # 2 bars
    "/16": 7   # 4 bars
}

# === FILTER ===
FILTER_TYPES = ["LP", "HP", "BP"]

# Filter name -> SuperCollider index
FILTER_TYPE_INDEX = {
    "LP": 0,
    "HP": 1,
    "BP": 2
}

# === BPM ===
BPM_DEFAULT = 120
BPM_MIN = 20
BPM_MAX = 300

# === GENERATORS ===
# Cycle order when clicking generator slot
# Other generators have SynthDefs ready but need testing
GENERATOR_CYCLE = ["Empty", "Test Synth", "PT2399"]

# Maximum custom params per generator
MAX_CUSTOM_PARAMS = 5

# Generator configs loaded from JSON files
# Maps display name -> {"synthdef": str, "custom_params": list}
_GENERATOR_CONFIGS = {}

def _load_generator_configs():
    """Load generator configs from JSON files in supercollider/generators/"""
    global _GENERATOR_CONFIGS
    
    # Find generators directory relative to this file
    config_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.dirname(config_dir)
    project_dir = os.path.dirname(src_dir)
    generators_dir = os.path.join(project_dir, 'supercollider', 'generators')
    
    _GENERATOR_CONFIGS = {"Empty": {"synthdef": None, "custom_params": []}}
    
    if not os.path.exists(generators_dir):
        print(f"Warning: Generators directory not found: {generators_dir}")
        return
    
    for filename in os.listdir(generators_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(generators_dir, filename)
            try:
                with open(filepath, 'r') as f:
                    config = json.load(f)
                    name = config.get('name')
                    if name:
                        _GENERATOR_CONFIGS[name] = {
                            "synthdef": config.get('synthdef'),
                            "custom_params": config.get('custom_params', [])[:MAX_CUSTOM_PARAMS]
                        }
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Failed to load {filepath}: {e}")
    
    # Validate GENERATOR_CYCLE
    for name in GENERATOR_CYCLE:
        if name != "Empty" and name not in _GENERATOR_CONFIGS:
            print(f"Warning: '{name}' in GENERATOR_CYCLE but no JSON found")

# Load on import
_load_generator_configs()

def get_generator_synthdef(name):
    """Get SynthDef name for a generator display name."""
    config = _GENERATOR_CONFIGS.get(name, {})
    return config.get('synthdef')

def get_generator_custom_params(name):
    """Get custom params list for a generator display name."""
    config = _GENERATOR_CONFIGS.get(name, {})
    return config.get('custom_params', [])

# Legacy GENERATORS dict for compatibility (built from JSON)
GENERATORS = {name: cfg['synthdef'] for name, cfg in _GENERATOR_CONFIGS.items()}

# === LFO ===
LFO_WAVEFORMS = ["SIN", "SAW", "SQR", "S&H"]
LFO_WAVEFORM_INDEX = {
    "SIN": 0,
    "SAW": 1,
    "SQR": 2,
    "S&H": 3
}

# === OSC ===
OSC_HOST = "127.0.0.1"
OSC_SEND_PORT = 57120
OSC_RECEIVE_PORT = 57121

OSC_PATHS = {
    'clock_bpm': '/noise/clock/bpm',
    'gen_frequency': '/noise/gen/frequency',
    'gen_cutoff': '/noise/gen/cutoff',
    'gen_resonance': '/noise/gen/resonance',
    'gen_attack': '/noise/gen/attack',
    'gen_decay': '/noise/gen/decay',
    'gen_filter_type': '/noise/gen/filterType',
    'gen_env_enabled': '/noise/gen/envEnabled',
    'gen_clock_rate': '/noise/gen/clockRate',
    'gen_custom': '/noise/gen/custom',  # /noise/gen/custom/{slot}/{param_index}
    'start_generator': '/noise/start_generator',
    'stop_generator': '/noise/stop_generator',
    'fidelity_amount': '/noise/fidelity_amount',
}

# === WIDGET SIZES ===
SIZES = {
    # Buttons
    'button_small': (20, 18),      # Mute/Solo
    'button_medium': (36, 24),     # Filter, ENV, Rate
    'button_large': (40, 20),      # LFO waveform
    'button_bpm': (28, 36),        # BPM arrows
    
    # Sliders
    'slider_width': 25,
    'slider_width_narrow': 20,
    'slider_height_small': 40,
    'slider_height_medium': 50,
    'slider_height_large': 80,
    
    # Containers
    'effect_slot_width': 70,
    'lfo_widget_width': 60,
    'buttons_column_width': 38,
}
