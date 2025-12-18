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
        'oct_range': 4,  # Modulation range in octaves
    },
    {
        'key': 'cutoff',
        'label': 'CUT',
        'tooltip': 'Filter Cutoff',
        'default': 1.0,  # Fully up = filter open
        'min': 20.0,     # 20Hz - match SC
        'max': 16000.0,
        'curve': 'exp',
        'unit': 'Hz',
        'invert': False,
        'oct_range': 4,  # Modulation range in octaves
    },
    {
        'key': 'resonance',
        'label': 'RES',
        'tooltip': 'Filter Resonance',
        'default': 0.0,  # Fully down = no resonance
        'min': 0.1,      # Match SC
        'max': 1.0,
        'curve': 'lin',  # Linear to match SC modulation
        'unit': '',
        'invert': True,  # High slider = low rq = more resonance
        'oct_range': 0,
    },
    {
        'key': 'attack',
        'label': 'ATK',
        'tooltip': 'VCA Attack',
        'default': 0.0,  # Snappiest
        'min': 0.0001,
        'max': 2.0,      # Match SC
        'curve': 'exp',
        'unit': 's',
        'invert': False,
        'oct_range': 0,  # Linear modulation
    },
    {
        'key': 'decay',
        'label': 'DEC',
        'tooltip': 'VCA Decay',
        'default': 0.73,  # 1s
        'min': 0.01,      # Match SC
        'max': 10.0,      # Match SC
        'curve': 'exp',
        'unit': 's',
        'invert': False,
        'oct_range': 0,  # Linear modulation
    },
]

# Build lookup dict for quick access
GENERATOR_PARAMS_BY_KEY = {p['key']: p for p in GENERATOR_PARAMS}

# Custom params (P1-P5) config for modulation
CUSTOM_PARAM_CONFIG = {
    'min': 0.0,
    'max': 1.0,
    'curve': 'lin',
    'oct_range': 0,
}


def get_param_config(param_key):
    """Get param config by key, including custom params."""
    if param_key.startswith('p') and len(param_key) == 2 and param_key[1].isdigit():
        return CUSTOM_PARAM_CONFIG
    return GENERATOR_PARAMS_BY_KEY.get(param_key, CUSTOM_PARAM_CONFIG)


def map_value(normalized, param):
    """
    Map normalized 0-1 slider value to real parameter value.
    Handles linear/exponential curves, inversion, and stepped params.
    """
    # Clamp normalized to valid range
    normalized = max(0.0, min(1.0, normalized))
    
    if param.get('invert', False):
        normalized = 1.0 - normalized
    
    # Quantize for stepped params (e.g. MODE 0/1/2)
    steps = param.get('steps')
    try:
        steps = int(steps) if steps is not None else None
    except (ValueError, TypeError):
        steps = None
    if steps and steps > 1:
        normalized = round(normalized * (steps - 1)) / (steps - 1)
    
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


def unmap_value(mapped, param):
    """
    Inverse of map_value: convert real parameter value back to normalized 0-1.
    Used for displaying current modulated values on sliders.
    """
    min_val = param.get('min', 0.0)
    max_val = param.get('max', 1.0)
    
    # Clamp to valid range
    mapped = max(min_val, min(max_val, mapped))
    
    if param.get('curve', 'lin') == 'exp':
        # Exponential: inverse is log
        if min_val <= 0:
            min_val = 0.001
        if max_val <= min_val:
            max_val = min_val * 1.001
        if mapped <= 0:
            mapped = min_val
        # norm = log(mapped/min) / log(max/min)
        normalized = math.log(mapped / min_val) / math.log(max_val / min_val)
    else:
        # Linear: inverse is simple
        if max_val == min_val:
            normalized = 0.5
        else:
            normalized = (mapped - min_val) / (max_val - min_val)
    
    # Apply invert (same as map_value, since it's symmetric)
    if param.get('invert', False):
        normalized = 1.0 - normalized
    
    return max(0.0, min(1.0, normalized))


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
# Core generator order (static list for preferred ordering)
# Pack generators are appended dynamically after these
_CORE_GENERATOR_ORDER = [
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

# Dynamic generator cycle (built after loading)
# Includes core generators + pack generators with separators
GENERATOR_CYCLE = []  # Populated by _finalize_config()

# Maximum custom params per generator
MAX_CUSTOM_PARAMS = 5

# Generator configs loaded from JSON files
# Maps display name -> {"synthdef": str, "custom_params": list, "pitch_target": int|None, "output_trim_db": float}
_GENERATOR_CONFIGS = {}

# === PACK SYSTEM ===
# Pack configs loaded from manifest.json files
# Maps pack_id (directory name) -> {id, display_name, version, author, enabled, generators, path}
_PACK_CONFIGS = {}

# Track which generators came from which pack (for UI grouping)
# Maps generator_name -> pack_id (None for core generators)
_GENERATOR_SOURCES = {}


def _discover_packs():
    """
    Scan packs/ directory for valid pack manifests.
    Populates _PACK_CONFIGS with metadata (does not load generators).
    
    Returns:
        dict: {pack_id: {id, display_name, version, author, enabled, generators, path}}
    """
    global _PACK_CONFIGS
    
    # Late import to avoid circular dependency at module load time
    try:
        from src.utils.logger import logger
    except ImportError:
        logger = None
    
    _PACK_CONFIGS = {}
    
    # Find packs directory relative to this file
    config_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.dirname(config_dir)
    project_dir = os.path.dirname(src_dir)
    packs_dir = os.path.join(project_dir, 'packs')
    
    if not os.path.exists(packs_dir):
        if logger:
            logger.debug("No packs/ directory found", component="PACKS")
        return _PACK_CONFIGS
    
    for entry in sorted(os.listdir(packs_dir)):
        pack_path = os.path.join(packs_dir, entry)
        
        # Skip files, hidden dirs, and special entries
        if not os.path.isdir(pack_path):
            continue
        if entry.startswith('.'):
            continue
        
        manifest_path = os.path.join(pack_path, 'manifest.json')
        if not os.path.exists(manifest_path):
            if logger:
                logger.warning(f"Pack '{entry}' missing manifest.json, skipping", component="PACKS")
            continue
        
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            
            # Validate required fields
            required = ['pack_format', 'name', 'enabled', 'generators']
            missing = [field for field in required if field not in manifest]
            if missing:
                if logger:
                    logger.warning(f"Pack '{entry}' manifest missing fields: {missing}", component="PACKS")
                continue
            
            # Check format version
            if manifest['pack_format'] != 1:
                if logger:
                    logger.warning(f"Pack '{entry}' has unsupported format version {manifest['pack_format']}", component="PACKS")
                continue
            
            pack_id = entry  # directory name = stable unique pack ID
            display_name = manifest['name']  # UI name (can collide, not used as key)
            
            _PACK_CONFIGS[pack_id] = {
                'id': pack_id,
                'display_name': display_name,
                'version': manifest.get('version', '0.0.0'),
                'author': manifest.get('author', 'Unknown'),
                'description': manifest.get('description', ''),
                'enabled': manifest.get('enabled', True),
                'generators': manifest.get('generators', []),
                'path': pack_path,
            }
            
            status = "enabled" if manifest.get('enabled', True) else "disabled"
            gen_count = len(manifest.get('generators', []))
            if logger:
                logger.info(
                    f"Found pack: {display_name} v{manifest.get('version', '?')} "
                    f"(id={pack_id}, {gen_count} generators, {status})",
                    component="PACKS"
                )
        
        except json.JSONDecodeError as e:
            if logger:
                logger.warning(f"Pack '{entry}' has invalid manifest.json: {e}", component="PACKS")
        except IOError as e:
            if logger:
                logger.warning(f"Failed to read pack '{entry}': {e}", component="PACKS")
    
    return _PACK_CONFIGS


def get_discovered_packs():
    """
    Get all discovered packs (enabled and disabled).
    
    Returns:
        dict: {pack_id: {id, display_name, version, author, enabled, generators, path}}
    """
    return _PACK_CONFIGS.copy()


def get_enabled_packs():
    """
    Get only enabled packs, in discovery order.
    
    Note: Returned dicts may be augmented during load (e.g., 'loaded_generators'
    is added by _load_generator_configs()).
    
    Returns:
        list: [{id, display_name, version, author, generators, path, ...}, ...]
    """
    return [p for p in _PACK_CONFIGS.values() if p.get('enabled', False)]


def get_generator_source(generator_name):
    """
    Get which pack a generator came from.
    
    Returns:
        str or None: Pack id (directory name), or None if core generator
    """
    return _GENERATOR_SOURCES.get(generator_name)

def _load_generator_configs():
    """Load generator configs from core + enabled packs."""
    global _GENERATOR_CONFIGS, _GENERATOR_SOURCES
    
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
    
    _GENERATOR_CONFIGS = {"Empty": {"synthdef": None, "custom_params": [], "pitch_target": None, "output_trim_db": 0.0}}
    _GENERATOR_SOURCES = {"Empty": None}  # None = core generator
    _LOADED_SYNTHDEFS = set()  # Track SynthDef symbols across core + packs
    
    # === LOAD CORE GENERATORS ===
    if not os.path.exists(generators_dir):
        if logger:
            logger.warning(f"Generators directory not found: {generators_dir}", component="CONFIG")
    else:
        for filename in os.listdir(generators_dir):
            # Skip non-JSON and hidden files (AppleDouble ._*.json, .DS_Store, etc.)
            if not filename.endswith('.json'):
                continue
            if filename.startswith('.'):
                continue
            
            filepath = os.path.join(generators_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    name = config.get('name')
                    synthdef = config.get('synthdef')
                    if name:
                        _GENERATOR_CONFIGS[name] = {
                            "synthdef": synthdef,
                            "custom_params": config.get('custom_params', [])[:MAX_CUSTOM_PARAMS],
                            "pitch_target": config.get('pitch_target'),  # None if not specified
                            "midi_retrig": config.get('midi_retrig', False),  # For struck/plucked generators
                            "output_trim_db": config.get('output_trim_db', 0.0)  # Loudness normalization
                        }
                        _GENERATOR_SOURCES[name] = None  # Mark as core
                        if synthdef:
                            _LOADED_SYNTHDEFS.add(synthdef)
            except UnicodeDecodeError as e:
                if logger:
                    logger.warning(f"Skipping non-UTF8 generator config: {filename} ({e})", component="CONFIG")
                continue
            except json.JSONDecodeError as e:
                if logger:
                    logger.warning(f"Skipping invalid JSON generator config: {filename} ({e})", component="CONFIG")
                continue
            except IOError as e:
                if logger:
                    logger.warning(f"Failed to load {filepath}: {e}", component="CONFIG")
    
    # === LOAD PACK GENERATORS ===
    for pack in get_enabled_packs():
        pack_generators_dir = os.path.join(pack['path'], 'generators')
        
        if not os.path.exists(pack_generators_dir):
            if logger:
                logger.warning(f"Pack '{pack['display_name']}' has no generators/ directory", component="PACKS")
            continue
        
        loaded_from_pack = []
        
        for gen_entry in pack['generators']:
            # Try file-stem match first (recommended), then display-name fallback
            json_file = None
            gen_name = None
            config = None
            
            # 1. Try file-stem match: gen_entry.json
            stem_path = os.path.join(pack_generators_dir, f"{gen_entry}.json")
            if os.path.exists(stem_path):
                try:
                    with open(stem_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        json_file = stem_path
                        gen_name = config.get('name', gen_entry)  # Use display name from JSON
                except (json.JSONDecodeError, IOError):
                    pass
            
            # 2. Fallback: search by display name
            if not json_file:
                for filename in os.listdir(pack_generators_dir):
                    if filename.endswith('.json') and not filename.startswith('.'):
                        filepath = os.path.join(pack_generators_dir, filename)
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                file_config = json.load(f)
                                if file_config.get('name') == gen_entry:
                                    json_file = filepath
                                    gen_name = gen_entry
                                    config = file_config
                                    break
                        except (json.JSONDecodeError, IOError):
                            continue
            
            if not json_file:
                if logger:
                    logger.warning(f"Pack '{pack['display_name']}': generator '{gen_entry}' not found", component="PACKS")
                continue
            
            # Check for display name conflicts with core
            if gen_name in _GENERATOR_CONFIGS and _GENERATOR_SOURCES.get(gen_name) is None:
                if logger:
                    logger.warning(f"Pack '{pack['display_name']}': '{gen_name}' conflicts with core generator, skipping", component="PACKS")
                continue
            
            # Check for display name conflicts with other packs
            if gen_name in _GENERATOR_CONFIGS:
                existing_pack = _GENERATOR_SOURCES.get(gen_name)
                if logger:
                    logger.warning(f"Pack '{pack['display_name']}': '{gen_name}' already loaded from '{existing_pack}', skipping", component="PACKS")
                continue
            
            # Validate SynthDef symbol uniqueness
            synthdef = config.get('synthdef')
            if not synthdef:
                if logger:
                    logger.warning(f"Pack '{pack['display_name']}': '{gen_name}' missing synthdef, skipping", component="PACKS")
                continue
            
            if synthdef in _LOADED_SYNTHDEFS:
                if logger:
                    logger.warning(
                        f"Pack '{pack['display_name']}': synthdef '{synthdef}' already loaded "
                        f"(conflicts with core/another pack), skipping '{gen_name}'",
                        component="PACKS"
                    )
                continue
            
            # Load the generator
            _GENERATOR_CONFIGS[gen_name] = {
                "synthdef": synthdef,
                "custom_params": config.get('custom_params', [])[:MAX_CUSTOM_PARAMS],
                "pitch_target": config.get('pitch_target'),
                "midi_retrig": config.get('midi_retrig', False),
                "output_trim_db": config.get('output_trim_db', 0.0),
                "pack": pack['id'],  # Track source pack
                "pack_path": pack['path'],
            }
            _GENERATOR_SOURCES[gen_name] = pack['id']
            _LOADED_SYNTHDEFS.add(synthdef)
            loaded_from_pack.append(gen_name)
        
        # Store resolved generator names for Phase 4 cycle building
        pack['loaded_generators'] = loaded_from_pack
        
        if logger and loaded_from_pack:
            logger.info(f"Loaded {len(loaded_from_pack)} generators from pack '{pack['display_name']}'", component="PACKS")
    
    # Note: GENERATOR_CYCLE validation moved to _finalize_config() after cycle is built


def _build_generator_cycle():
    """
    Build complete generator list: core + enabled packs.
    
    Returns:
        list: Ordered generator names for UI dropdown (includes separators)
    """
    cycle = []
    
    # 1. Core generators (in defined order)
    for name in _CORE_GENERATOR_ORDER:
        if name in _GENERATOR_CONFIGS:
            cycle.append(name)
    
    # 2. Pack generators (grouped by pack, in manifest order)
    for pack in get_enabled_packs():
        # Use resolved display names stored during loading (preserves manifest order)
        pack_generators = pack.get('loaded_generators', [])
        
        if pack_generators:
            # Add separator (special entry, handled by UI)
            cycle.append(f"──── {pack['display_name']} ────")
            cycle.extend(pack_generators)
    
    return cycle


def get_valid_generators():
    """
    Get generator names only (no separators).
    
    CANONICAL accessor - use this everywhere you need a list of selectable generator names.
    
    Returns:
        list: Generator names that can be selected (excludes separator entries)
    """
    return [g for g in GENERATOR_CYCLE if not g.startswith("────")]


def _finalize_config():
    """Called after all loading complete to build dynamic lists."""
    global GENERATOR_CYCLE
    
    # Late import to avoid circular dependency
    try:
        from src.utils.logger import logger
    except ImportError:
        logger = None
    
    GENERATOR_CYCLE = _build_generator_cycle()
    
    # Validate core generators exist
    for name in _CORE_GENERATOR_ORDER:
        if name != "Empty" and name not in _GENERATOR_CONFIGS:
            if logger:
                logger.warning(f"'{name}' in _CORE_GENERATOR_ORDER but no JSON found", component="CONFIG")


# Load on import - ORDER MATTERS
_discover_packs()           # 1. Find packs
_load_generator_configs()   # 2. Load core + pack generators
_finalize_config()          # 3. Build GENERATOR_CYCLE

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

def get_generator_output_trim_db(name):
    """Get output trim in dB for a generator.
    
    Used for loudness normalization - hot generators get negative trim.
    Applied in channel strip before other processing.
    
    Returns:
        float: Trim in dB (0.0 = no trim, -6.0 = -6dB, etc.)
    """
    config = _GENERATOR_CONFIGS.get(name, {})
    return config.get('output_trim_db', 0.0)

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

# === MOD SOURCES ===
# Slot and bus counts
MOD_SLOT_COUNT = 4
MOD_OUTPUTS_PER_SLOT = 4  # Quadrature: A/B/C/D or X/Y/Z/R
MOD_BUS_COUNT = MOD_SLOT_COUNT * MOD_OUTPUTS_PER_SLOT  # 16

# Mod generator cycle (like GENERATOR_CYCLE)
MOD_GENERATOR_CYCLE = [
    "Empty",
    "LFO",
    "Sloth",
]

# LFO waveforms (TTLFO v2 inspired)
MOD_LFO_WAVEFORMS = ["Saw", "Ramp", "Sqr", "Tri", "Sin", "Rect+", "Rect-", "S&H"]
MOD_LFO_WAVEFORM_INDEX = {w: i for i, w in enumerate(MOD_LFO_WAVEFORMS)}

# LFO phase steps (degrees)
MOD_LFO_PHASES = [0, 45, 90, 135, 180, 225, 270, 315]
MOD_LFO_PHASE_INDEX = {p: i for i, p in enumerate(MOD_LFO_PHASES)}

# LFO quadrature phase patterns (degrees for A, B, C, D)
MOD_LFO_PHASE_PATTERNS = {
    "QUAD":   [0, 90, 180, 270],   # Classic quadrature
    "PAIR":   [0, 0, 180, 180],    # Two pairs, 180° apart
    "SPREAD": [0, 45, 180, 225],   # Spread across cycle
    "TIGHT":  [0, 22, 45, 67],     # Tight cluster
    "WIDE":   [0, 120, 180, 300],  # Wide spread
    "SYNC":   [0, 0, 0, 0],        # All in phase
}
MOD_LFO_PHASE_PATTERN_NAMES = list(MOD_LFO_PHASE_PATTERNS.keys())
MOD_LFO_ROTATE_STEPS = 24  # 15° per step (360/24)

# LFO sync modes
MOD_LFO_MODES = ["CLK", "FREE"]  # CLK = clock synced, FREE = manual frequency
MOD_LFO_MODE_INDEX = {m: i for i, m in enumerate(MOD_LFO_MODES)}

# LFO free-running frequency range (Hz)
MOD_LFO_FREQ_MIN = 0.01   # ~100 second cycle
MOD_LFO_FREQ_MAX = 100.0  # Audio rate modulation

# Sloth speed modes (NLC Triple Sloth inspired)
MOD_SLOTH_MODES = ["Torpor", "Apathy", "Inertia"]
MOD_SLOTH_MODE_INDEX = {m: i for i, m in enumerate(MOD_SLOTH_MODES)}

# Clock rates for mod sources - full range
# Slowest to fastest: /64 (16 bars) to x32 (1/128th note)
MOD_CLOCK_RATES = ["/64", "/32", "/16", "/8", "/4", "/2", "1", "x2", "x4", "x8", "x16", "x32"]
MOD_CLOCK_RATE_INDEX = {r: i for i, r in enumerate(MOD_CLOCK_RATES)}

# Clock source index (which channel of ~clockTrigBus to use)
# Index 12 = x32 clock (32 ticks per quarter note)
MOD_CLOCK_SOURCE_INDEX = 12
MOD_CLOCK_TICKS_PER_QUARTER = 32  # Derived from x32 clock

# Ticks per LFO cycle for each rate (at x32 resolution)
# Must match MOD_CLOCK_RATES order
# /64=2048, /32=1024, /16=512, /8=256, /4=128, /2=64, 1=32, x2=16, x4=8, x8=4, x16=2, x32=1
MOD_CLOCK_TICKS_PER_CYCLE = [2048, 1024, 512, 256, 128, 64, 32, 16, 8, 4, 2, 1]

# Polarity options
MOD_POLARITY = ["NORM", "INV"]
MOD_POLARITY_INDEX = {"NORM": 0, "INV": 1}

# Output labels by generator type (4 outputs each)
MOD_OUTPUT_LABELS = {
    "Empty": ["A", "B", "C", "D"],
    "LFO": ["A", "B", "C", "D"],      # Quadrature phases
    "Sloth": ["X", "Y", "Z", "R"],    # R = rectified gate
}

# Mod generator configs loaded from JSON files
_MOD_GENERATOR_CONFIGS = {}

def _load_mod_generator_configs():
    """Load mod generator configs from JSON files in supercollider/mod_generators/"""
    global _MOD_GENERATOR_CONFIGS
    
    try:
        from src.utils.logger import logger
    except ImportError:
        logger = None
    
    config_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.dirname(config_dir)
    project_dir = os.path.dirname(src_dir)
    mod_generators_dir = os.path.join(project_dir, 'supercollider', 'mod_generators')
    
    _MOD_GENERATOR_CONFIGS = {
        "Empty": {
            "synthdef": None,
            "custom_params": [],
            "output_config": "fixed",
            "outputs": ["A", "B", "C", "D"]
        }
    }
    
    if not os.path.exists(mod_generators_dir):
        if logger:
            logger.debug(f"Mod generators directory not found: {mod_generators_dir}", component="CONFIG")
        return
    
    for filename in os.listdir(mod_generators_dir):
        # Skip non-JSON and hidden files (AppleDouble ._*.json, .DS_Store, etc.)
        if not filename.endswith('.json'):
            continue
        if filename.startswith('.'):
            continue
        
        filepath = os.path.join(mod_generators_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                config = json.load(f)
                name = config.get('name')
                if name:
                    _MOD_GENERATOR_CONFIGS[name] = {
                        "synthdef": config.get('synthdef'),
                        "custom_params": config.get('custom_params', []),
                        "output_config": config.get('output_config', 'fixed'),
                        "outputs": config.get('outputs', ['A', 'B', 'C', 'D'])
                    }
        except UnicodeDecodeError as e:
            if logger:
                logger.warning(f"Skipping non-UTF8 mod generator config: {filename} ({e})", component="CONFIG")
            continue
        except json.JSONDecodeError as e:
            if logger:
                logger.warning(f"Skipping invalid JSON mod generator config: {filename} ({e})", component="CONFIG")
            continue
        except IOError as e:
            if logger:
                logger.warning(f"Failed to load mod generator {filepath}: {e}", component="CONFIG")
    
    # Validate MOD_GENERATOR_CYCLE
    for name in MOD_GENERATOR_CYCLE:
        if name != "Empty" and name not in _MOD_GENERATOR_CONFIGS:
            if logger:
                logger.warning(f"'{name}' in MOD_GENERATOR_CYCLE but no JSON found", component="CONFIG")

# Load on import
_load_mod_generator_configs()

def get_mod_generator_synthdef(name):
    """Get SynthDef name for a mod generator."""
    config = _MOD_GENERATOR_CONFIGS.get(name, {})
    return config.get('synthdef')

def get_mod_generator_custom_params(name):
    """Get custom params list for a mod generator."""
    config = _MOD_GENERATOR_CONFIGS.get(name, {})
    return config.get('custom_params', [])

def get_mod_generator_output_config(name):
    """Get output config type for a mod generator.
    
    Returns:
        'waveform_phase': Show waveform and phase selectors per output (LFO)
        'fixed': Show fixed output labels only (Sloth, Empty)
    """
    config = _MOD_GENERATOR_CONFIGS.get(name, {})
    return config.get('output_config', 'fixed')

def get_mod_output_labels(name):
    """Get output labels for a mod generator.
    
    Returns:
        List of 3 strings, e.g. ['A', 'B', 'C'] or ['X', 'Y', 'Z']
    """
    return MOD_OUTPUT_LABELS.get(name, ["A", "B", "C"])

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
    'gen_strip_solo': '/noise/gen/solo',
    'gen_gain': '/noise/gen/gain',  # Per-channel gain stage (0dB, +6dB, +12dB)
    'gen_pan': '/noise/gen/pan',  # Per-channel pan (-1=L, 0=center, 1=R)
    'gen_strip_eq_base': '/noise/strip/eq',  # Per-channel EQ: /noise/strip/eq/{band}
    'gen_levels': '/noise/gen/levels',  # Per-channel level metering
    'gen_trim': '/noise/gen/trim',  # Per-channel loudness trim (from JSON config)
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
    # Master Compressor
    'master_comp_threshold': '/noise/master/comp/threshold',
    'master_comp_ratio': '/noise/master/comp/ratio',
    'master_comp_attack': '/noise/master/comp/attack',
    'master_comp_release': '/noise/master/comp/release',
    'master_comp_makeup': '/noise/master/comp/makeup',
    'master_comp_sc_hpf': '/noise/master/comp/sc_hpf',
    'master_comp_bypass': '/noise/master/comp/bypass',
    'master_comp_gr': '/noise/master/comp/gr',
    # Audio device
    'audio_devices_query': '/noise/audio/devices/query',
    'audio_devices_count': '/noise/audio/devices/count',
    'audio_devices_item': '/noise/audio/devices/item',
    'audio_devices_done': '/noise/audio/devices/done',
    'audio_device_set': '/noise/audio/device/set',
    'audio_device_changing': '/noise/audio/device/changing',
    'audio_device_ready': '/noise/audio/device/ready',
    'audio_device_error': '/noise/audio/device/error',
    # Mod sources
    'mod_generator': '/noise/mod/generator',        # /noise/mod/generator/{slot}
    'mod_param': '/noise/mod/param',                # /noise/mod/param/{slot}/{key}
    'mod_output_wave': '/noise/mod/out/wave',       # /noise/mod/out/wave/{slot}/{output}
    'mod_output_phase': '/noise/mod/out/phase',     # /noise/mod/out/phase/{slot}/{output}
    'mod_output_polarity': '/noise/mod/out/pol',    # /noise/mod/out/pol/{slot}/{output}
    'mod_bus_value': '/noise/mod/bus/value',        # /noise/mod/bus/value/{bus} (SC → Python)
    'mod_scope_enable': '/noise/mod/scope/enable',  # /noise/mod/scope/enable/{slot} (Python → SC)
    
    # Mod routing (connections between mod buses and generator params)
    # Protocol: add/set/remove with full params (depth, amount, offset, polarity, invert)
    'mod_route_add': '/noise/mod/route/add',        # [bus, slot, param, depth, amount, offset, polarity, invert]
    'mod_route_set': '/noise/mod/route/set',        # [bus, slot, param, depth, amount, offset, polarity, invert]
    'mod_route_remove': '/noise/mod/route/remove',  # [bus, slot, param]
}

# === WIDGET SIZES ===
SIZES = {
    # Buttons
    'button_small': (20, 18),      # Mute/Solo
    'button_medium': (36, 24),     # Filter, ENV, Rate
    'button_large': (40, 20),      # LFO waveform
    'button_bpm': (28, 36),        # BPM arrows
    
    # Sliders (legacy fixed heights)
    'slider_width': 25,
    'slider_width_narrow': 20,
    'slider_height_small': 40,
    'slider_height_medium': 50,
    'slider_height_large': 80,
    
    # Fader constraints by context (min, max) - for scaling displays
    # Mixer channel faders - main mixing controls
    'fader_mixer_min': 80,
    'fader_mixer_max': 200,
    
    # Master volume fader - matches mixer
    'fader_master_min': 80,
    'fader_master_max': 200,
    
    # EQ sliders - shorter, compact section
    'fader_eq_min': 50,
    'fader_eq_max': 120,
    
    # Compressor sliders (threshold, makeup) - compact
    'fader_comp_min': 50,
    'fader_comp_max': 100,
    
    # Limiter ceiling - compact
    'fader_limiter_min': 50,
    'fader_limiter_max': 100,
    
    # Generator param sliders - compact but scalable
    'fader_generator_min': 60,
    'fader_generator_max': 120,
    
    # Containers
    'effect_slot_width': 70,
    'lfo_widget_width': 60,
    'buttons_column_width': 44,
    
    # Layout spacing (global)
    'spacing_tight': 2,       # Within compact widgets
    'spacing_normal': 4,      # Between related elements  
    'spacing_section': 6,     # Between sections/panels
    'margin_none': 0,         # Panels that butt together
    'margin_tight': 4,        # Compact internal margins
    'margin_normal': 8,       # Standard internal margins
}
