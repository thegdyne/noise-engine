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
        'min': 20.0,
        'max': 8000.0,
        'curve': 'exp',
        'unit': 'Hz',
        'invert': False,
    },
    {
        'key': 'cutoff',
        'label': 'CUT',
        'tooltip': 'Filter Cutoff',
        'default': 1.0,  # Fully up = filter open
        'min': 1.0,      # 1Hz - effectively closed
        'max': 16000.0,
        'curve': 'exp',
        'unit': 'Hz',
        'invert': False,
    },
    {
        'key': 'resonance',
        'label': 'RES',
        'tooltip': 'Filter Resonance',
        'default': 0.0,  # Fully down = no resonance
        'min': 0.001,    # Self-oscillation territory
        'max': 1.0,
        'curve': 'exp',  # Exponential - gets intense at top
        'unit': '',
        'invert': True,  # High slider = low rq = more resonance
    },
    {
        'key': 'attack',
        'label': 'ATK',
        'tooltip': 'VCA Attack',
        'default': 0.0,  # Snappiest
        'min': 0.0001,
        'max': 0.5,
        'curve': 'exp',
        'unit': 's',
        'invert': False,
    },
    {
        'key': 'decay',
        'label': 'DEC',
        'tooltip': 'VCA Decay',
        'default': 0.73,  # 1s
        'min': 0.0001,    # 0.1ms - super snappy
        'max': 30.0,      # 30 seconds - Maths-style range
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
    # Clamp normalized to valid range
    normalized = max(0.0, min(1.0, normalized))
    
    if param.get('invert', False):
        normalized = 1.0 - normalized
    
    min_val = param.get('min', 0.0)
    max_val = param.get('max', 1.0)
    
    if param.get('curve', 'lin') == 'exp':
        # Exponential mapping (need non-zero min)
        if min_val <= 0:
            min_val = 0.001  # Prevent division by zero
        if max_val <= 0:
            max_val = 1.0
        result = min_val * math.pow(max_val / min_val, normalized)
    else:
        # Linear mapping
        result = min_val + (max_val - min_val) * normalized
    
    # Clamp result to prevent float overflow in OSC
    # IEEE 754 single-precision float max is ~3.4e38
    result = max(-1e30, min(1e30, result))
    
    # Handle NaN/Inf
    if math.isnan(result) or math.isinf(result):
        result = float(param.get('default', 0.5))
    
    return result


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
CLOCK_RATES = ["/32", "/16", "/12", "/8", "/4", "/2", "CLK", "x2", "x4", "x8", "x12", "x16", "x32"]
CLOCK_DEFAULT_INDEX = 6  # CLK

# Rate name -> SuperCollider index (auto-generated from CLOCK_RATES for SSOT)
CLOCK_RATE_INDEX = {rate: i for i, rate in enumerate(CLOCK_RATES)}

# === ENVELOPE SOURCE ===
ENV_SOURCES = ["OFF", "CLK", "MIDI"]
ENV_SOURCE_INDEX = {source: i for i, source in enumerate(ENV_SOURCES)}

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
# All generators now have SynthDefs with standard signal flow
GENERATOR_CYCLE = [
    "Empty",
    # Basic synthesis
    "Test Synth",
    "Subtractive",
    "Additive",
    "FM",
    "Wavetable",
    "Granular",
    # Physical modeling
    "Karplus",
    "Modal",
    # Relaxation oscillators (Elektor-inspired)
    "VCO Relax",
    "UJT Relax",
    "Neon",
    "CapSense",
    # Siren circuits (Elektor-inspired)
    "4060 Siren",
    "FBI Siren",
    "FBI Doppler",
    # Ring modulators (Elektor Formant)
    "Diode Ring",
    "4-Quad Ring",
    "VCA Ring",
    # Noise/chaos
    "PT2399",
    "PT Chaos",
    "Geiger",
    "Giant B0N0",
]

# Maximum custom params per generator
MAX_CUSTOM_PARAMS = 5

# Generator configs loaded from JSON files
# Maps display name -> {"synthdef": str, "custom_params": list, "pitch_target": int|None}
_GENERATOR_CONFIGS = {}

def _load_generator_configs():
    """Load generator configs from JSON files in supercollider/generators/"""
    global _GENERATOR_CONFIGS
    
    # Late import to avoid circular dependency at module load time
    try:
        from src.utils.logger import logger
    except ImportError:
        logger = None
    
    # Find generators directory relative to this file
    config_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.dirname(config_dir)
    project_dir = os.path.dirname(src_dir)
    generators_dir = os.path.join(project_dir, 'supercollider', 'generators')
    
    _GENERATOR_CONFIGS = {"Empty": {"synthdef": None, "custom_params": [], "pitch_target": None}}
    
    if not os.path.exists(generators_dir):
        if logger:
            logger.warning(f"Generators directory not found: {generators_dir}", component="CONFIG")
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
                            "custom_params": config.get('custom_params', [])[:MAX_CUSTOM_PARAMS],
                            "pitch_target": config.get('pitch_target'),  # None if not specified
                            "midi_retrig": config.get('midi_retrig', False)  # For struck/plucked generators
                        }
            except (json.JSONDecodeError, IOError) as e:
                if logger:
                    logger.warning(f"Failed to load {filepath}: {e}", component="CONFIG")
    
    # Validate GENERATOR_CYCLE
    for name in GENERATOR_CYCLE:
        if name != "Empty" and name not in _GENERATOR_CONFIGS:
            if logger:
                logger.warning(f"'{name}' in GENERATOR_CYCLE but no JSON found", component="CONFIG")

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

def get_generator_pitch_target(name):
    """Get pitch target for a generator.
    
    Returns:
        None: FRQ is the pitch param (normal)
        0-4: Custom param index is the pitch param
    """
    config = _GENERATOR_CONFIGS.get(name, {})
    return config.get('pitch_target')

def get_generator_midi_retrig(name):
    """Check if generator needs MIDI retriggering.
    
    For struck/plucked generators (modal, karplus), MIDI mode needs
    continuous retriggering while key is held, not just a single strike.
    
    Returns:
        bool: True if generator needs MIDI retrig behaviour
    """
    config = _GENERATOR_CONFIGS.get(name, {})
    return config.get('midi_retrig', False)

def get_generator_retrig_param_index(name):
    """Get the index of the retrig_rate param if it exists.
    
    Returns:
        int or None: Index (0-4) of retrig param, or None if not found
    """
    config = _GENERATOR_CONFIGS.get(name, {})
    params = config.get('custom_params', [])
    for i, param in enumerate(params):
        if param.get('key') == 'retrig_rate':
            return i
    return None

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
    # Global params
    'gravity': '/noise/gravity',
    'density': '/noise/density',
    'filter_cutoff': '/noise/filter_cutoff',
    'amplitude': '/noise/amplitude',
    # Per-generator params
    'gen_frequency': '/noise/gen/frequency',
    'gen_cutoff': '/noise/gen/cutoff',
    'gen_resonance': '/noise/gen/resonance',
    'gen_attack': '/noise/gen/attack',
    'gen_decay': '/noise/gen/decay',
    'gen_filter_type': '/noise/gen/filterType',
    'gen_env_enabled': '/noise/gen/envEnabled',
    'gen_env_source': '/noise/gen/envSource',  # 0=OFF, 1=CLK, 2=MIDI
    'gen_clock_rate': '/noise/gen/clockRate',
    'gen_mute': '/noise/gen/mute',
    'gen_midi_channel': '/noise/gen/midiChannel',
    'gen_custom': '/noise/gen/custom',  # /noise/gen/custom/{slot}/{param_index}
    'start_generator': '/noise/start_generator',
    'stop_generator': '/noise/stop_generator',
    'fidelity_amount': '/noise/fidelity_amount',
    # Channel strip (mixer)
    'gen_volume': '/noise/gen/volume',
    # Remove this line - gen_mute already exists with same path
    'gen_strip_solo': '/noise/gen/solo',
    'gen_gain': '/noise/gen/gain',  # Per-channel gain stage (0dB, +6dB, +12dB)
    'gen_pan': '/noise/gen/pan',  # Per-channel pan (-1=L, 0=center, 1=R)
    'gen_levels': '/noise/gen/levels',  # Per-channel level metering
    # MIDI
    'midi_device': '/noise/midi/device',
    'midi_gate': '/noise/midi/gate',  # SC -> Python for LED flash
    'midi_retrig': '/noise/gen/midiRetrig',  # Flag for MIDI continuous retriggering
    # Connection management
    'ping': '/noise/ping',
    'pong': '/noise/pong',
    'heartbeat': '/noise/heartbeat',
    'heartbeat_ack': '/noise/heartbeat_ack',
    # Master section
    'master_volume': '/noise/master/volume',
    'master_levels': '/noise/master/levels',
    'master_meter_toggle': '/noise/master/meter/toggle',
    'master_limiter_ceiling': '/noise/master/limiter/ceiling',
    'master_limiter_bypass': '/noise/master/limiter/bypass',
    # Master EQ
    'master_eq_lo': '/noise/master/eq/lo',
    'master_eq_mid': '/noise/master/eq/mid',
    'master_eq_hi': '/noise/master/eq/hi',
    'master_eq_lo_kill': '/noise/master/eq/lo/kill',
    'master_eq_mid_kill': '/noise/master/eq/mid/kill',
    'master_eq_hi_kill': '/noise/master/eq/hi/kill',
    'master_eq_locut': '/noise/master/eq/locut',
    'master_eq_bypass': '/noise/master/eq/bypass',
    # Audio device
    'audio_devices_query': '/noise/audio/devices/query',
    'audio_devices_count': '/noise/audio/devices/count',
    'audio_devices_item': '/noise/audio/devices/item',
    'audio_devices_done': '/noise/audio/devices/done',
    'audio_device_set': '/noise/audio/device/set',
    'audio_device_changing': '/noise/audio/device/changing',
    'audio_device_ready': '/noise/audio/device/ready',
    'audio_device_error': '/noise/audio/device/error',
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
    'buttons_column_width': 44,
}
