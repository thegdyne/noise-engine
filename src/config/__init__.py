"""
Central Configuration
All constants, mappings, and settings in one place
"""

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
# Display name -> SuperCollider SynthDef name
GENERATORS = {
    "Empty": None,
    "Test Synth": "testSynth",
    "PT2399": "pt2399Grainy",
}

# Cycle order when clicking generator slot
GENERATOR_CYCLE = ["Empty", "Test Synth", "PT2399"]

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
