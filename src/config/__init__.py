"""
Central Configuration
All constants, mappings, and settings in one place
"""

import math
import json
import os
from typing import List, Optional, Dict

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
    """Get param config by key, including custom params.

    Recognizes both 'p0'..'p4' and 'custom0'..'custom4' prefixes
    for unified bus targets.
    """
    if param_key.startswith('p') and len(param_key) == 2 and param_key[1].isdigit():
        return CUSTOM_PARAM_CONFIG
    if param_key.startswith('custom') and param_key[6:].isdigit():
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

# === TRANSPOSE ===
TRANSPOSE_OPTIONS = ["-2", "-1", "0", "+1", "+2"]  # Display strings (octaves)
TRANSPOSE_SEMITONES = [-24, -12, 0, 12, 24]  # Actual semitone values
TRANSPOSE_DEFAULT_INDEX = 2  # Middle = 0 semitones

# Rate name -> SuperCollider index (auto-generated from CLOCK_RATES for SSOT)
CLOCK_RATE_INDEX = {rate: i for i, rate in enumerate(CLOCK_RATES)}

# === ENVELOPE SOURCE ===
ENV_SOURCES = ["OFF", "CLK", "MIDI"]
ENV_SOURCE_INDEX = {source: i for i, source in enumerate(ENV_SOURCES)}

# === FILTER ===
FILTER_TYPES = ["LP", "HP", "BP", "NOT", "LP2", "OFF"]

# Filter name -> SuperCollider index
FILTER_TYPE_INDEX = {
    "LP": 0,
    "HP": 1,
    "BP": 2,
    "NOT": 3,
    "LP2": 4,
    "OFF": 5
}

# === ANALOG OUTPUT STAGE ===
ANALOG_TYPES = ["CLEAN", "TAPE", "TUBE", "FOLD"]  # SC internal (type bus 0-3)
ANALOG_TYPE_INDEX = {name: i for i, name in enumerate(ANALOG_TYPES)}
ANALOG_UI_LABELS = ["OFF", "CLEAN", "TAPE", "TUBE", "FOLD"]  # UI macro (OFF=bypass)

# === BPM ===
BPM_DEFAULT = 120
BPM_MIN = 20
BPM_MAX = 300

# === FX SYSTEM DEFAULTS ===
FX_ECHO_RETURN_DEFAULT = 0.5
FX_VERB_RETURN_DEFAULT = 0.85
FX_SLOT_ECHO_SEND_DEFAULT = 0.0
FX_SLOT_VERB_SEND_DEFAULT = 0.0

# === GENERATORS ===
# Core generator order (static list for preferred ordering)
# Pack generators are appended dynamically after these
_CORE_GENERATOR_ORDER = [
    "Empty",
    # Classic synths
    "TB-303",
    "Juno",
    "SH-101",
    "MS-20",
    "C64 SID",
    "Buchla",
    "B258 Master",
    "B258 Extreme",
    "B258 Dual Morph",
    "B258 Dual Osc",
    "Reference Sine",
    "Drone",
    # 808 Drums
    "808 Kick",
    "808 Snare",
    "808 Hat",
    "808 Clap",
    # Conceptual
    "THOR",
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
    # Test / diagnostic
    "Scope Test",
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
    
    # Clear in place to preserve external references (important for tests)
    _PACK_CONFIGS.clear()
    
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
        if entry.startswith('.') or entry.startswith('_'):
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
# Current pack selection (None = Core, or pack_id string)
_CURRENT_PACK = None


def get_current_pack():
    """
    Get currently selected pack.
    
    Returns:
        str or None: Pack id, or None for Core
    """
    return _CURRENT_PACK


def set_current_pack(pack_id):
    """
    Set current pack. Validates pack exists.
    
    Args:
        pack_id: Pack id string, or None for Core
        
    Returns:
        bool: True if pack was set, False if pack not found
    """
    global _CURRENT_PACK
    
    if pack_id is None:
        _CURRENT_PACK = None
        return True

    if pack_id == "__all__":
        _CURRENT_PACK = "__all__"
        return True

    if pack_id in _PACK_CONFIGS and _PACK_CONFIGS[pack_id].get('enabled', False):
        _CURRENT_PACK = pack_id
        return True

    # Pack not found, fall back to Core
    _CURRENT_PACK = None
    return False


def get_generators_for_pack(pack_id=None):
    """
    Get generator names for a specific pack (or Core).
    
    Args:
        pack_id: Pack id, or None for Core generators
        
    Returns:
        list: Generator names in order, always starts with "Empty"
    """
    result = ["Empty"]
    
    if pack_id is None:
        # Core generators: those with source = None
        for name, source in _GENERATOR_SOURCES.items():
            if source is None and name != "Empty":
                result.append(name)
    else:
        # Pack generators: those with matching source
        pack = _PACK_CONFIGS.get(pack_id)
        if pack and 'loaded_generators' in pack:
            result.extend(pack['loaded_generators'])
    
    return result


def get_current_generators():
    """
    Get generators for currently selected pack.

    Returns:
        list: Generator names for current pack (or Core)
    """
    return get_generators_for_pack(_CURRENT_PACK)


def get_all_pack_generators():
    """
    Get all generators from all enabled packs (no core, no separators).

    Returns:
        list: ["Empty"] + all pack generator names in pack order
    """
    result = ["Empty"]
    for pack in get_enabled_packs():
        result.extend(pack.get('loaded_generators', []))
    return result



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
    generators_dir = os.path.join(project_dir, 'packs', 'core', 'generators')
    
    # Clear in place to preserve external references (important for tests)
    _GENERATOR_CONFIGS.clear()
    _GENERATOR_CONFIGS["Empty"] = {"synthdef": None, "custom_params": [], "pitch_target": None, "output_trim_db": 0.0}
    _GENERATOR_SOURCES.clear()
    _GENERATOR_SOURCES["Empty"] = None  # None = core generator
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
                            "output_trim_db": config.get('output_trim_db', 0.0),  # Loudness normalization
                            "synthesis_method": config.get('synthesis_method', '')  # For SynthesisIcon display
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
                "synthesis_method": config.get('synthesis_method', ''),  # For SynthesisIcon display
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
        if pack['id'] == 'core':
            continue  # Core generators already added above
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
    
    # Clear and extend in place to preserve external references (important for tests)
    GENERATOR_CYCLE.clear()
    GENERATOR_CYCLE.extend(_build_generator_cycle())
    
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


def get_generator_synthesis_category(name):
    """Get synthesis method category for a generator.

    Returns:
        str: Category like 'fm', 'physical', 'texture', etc.
             Returns 'empty' for Empty generator, 'unknown' if not found.
    """
    if name == 'Empty':
        return 'empty'
    config = _GENERATOR_CONFIGS.get(name, {})
    method = config.get('synthesis_method', '')
    if '/' in method:
        return method.split('/')[0]
    return 'unknown'

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

# Cross-modulation buses (source IDs 16-23)
CROSSMOD_BUS_OFFSET = 16
CROSSMOD_BUS_COUNT = 8

# Mod generator cycle (like GENERATOR_CYCLE)
MOD_GENERATOR_CYCLE = [
    "Empty",
    "LFO",
    "Sloth",
    "ARSEq+",
    "SauceOfGrav",
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

# ARSEq+ time ranges (in seconds)
ARSEQ_SYNC_TIME_MIN = 0.0001   # 0.1ms
ARSEQ_SYNC_TIME_MAX = 10.0     # 10s
ARSEQ_LOOP_TIME_MIN = 0.0001   # 0.1ms
ARSEQ_LOOP_TIME_MAX = 120.0    # 2 minutes

# === SauceOfGrav v1.4.3 Config Constants ===

# Rate ranges
SAUCE_FREE_RATE_MIN = 0.001    # Hz
SAUCE_FREE_RATE_MAX = 100.0    # Hz
SAUCE_RATE_DEADBAND = 0.05     # 0-0.05 = OFF

# Noise / thresholds
SAUCE_NOISE_RATE = 0.012
SAUCE_VELOCITY_EPSILON = 0.001

# Mass mapping
MASS_BASE = 0.25
MASS_GAIN = 2.1

# Coupling
HUB_COUPLE_BASE = 0.0
HUB_COUPLE_GAIN = 6.0
HUB_TENSION_EXP = 0.70
RING_COUPLE_BASE = 0.0
RING_COUPLE_GAIN = 3.5
RING_TENSION_EXP = 1.30

# Non-reciprocal ring
RING_SKEW = 0.015

# Gravity stiffness
GRAV_STIFF_BASE = 0.0
GRAV_STIFF_GAIN = 6.0

# Excursion
EXCURSION_MIN = 0.60
EXCURSION_MAX = 1.60

# CALM macro (v1.4.3)
CALM_DAMP_CALM = 1.30
CALM_DAMP_WILD = 0.75
CALM_VDP_CALM = 0.90
CALM_VDP_WILD = 1.15
CALM_KICK_CALM = 0.60

# Van der Pol
VDP_INJECT = 0.8
VDP_THRESHOLD = 0.35
VDP_HUB_MOD = 0.05
VDP_THRESHOLD_FLOOR = 0.05

# Calibration trims
TENSION_TRIM = [+0.012, -0.008, +0.015, -0.018]
MASS_TRIM = [-0.010, +0.014, -0.006, +0.011]

# Damping
SAUCE_DAMPING_BASE = 0.10
SAUCE_DAMPING_TENSION = 0.40

# Rails
SAUCE_RAIL_ZONE = 0.08
SAUCE_RAIL_ABSORB = 0.35

# Resonance
RESO_FLOOR_MIN = 0.0002
RESO_FLOOR_MAX = 0.0040
RESO_DRIVE_GAIN = 6.0
RESO_DELTAE_MAX = 0.01
RESO_RAIL_EXP = 1.4

# Kickstart
RESO_KICK_GAIN = 2.8
RESO_KICK_MAXF = 0.30
RESO_KICK_COOLDOWN_S = 0.20
KICK_PATTERNS = [
    [+1, -1, +1, -1],
    [+1, +1, -1, -1],
    [+1, -1, -1, +1],
]

# Hub dynamics
OVERSHOOT_TO_HUB_GAIN = 0.6
OVERSHOOT_MAX = 0.25
HUB_LIMIT = 2.0
DEPTH_DAMP_MIN = 0.005
DEPTH_DAMP_MAX = 2.50

# Hub feed
HUB_FEED_GAIN = 8.0
HUB_FEED_MAX = 0.35

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
    "Sloth": ["X", "Y", "Z", "R"],  # R = rectified gate
    "ARSEq+": ["1", "2", "3", "4"],  # Envelope outputs
    "SauceOfGrav": ["1", "2", "3", "4"],  # Coupled outputs
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

# LFO config (programmatic registration)
_MOD_GENERATOR_CONFIGS["LFO"] = {
    "internal_id": "lfo",
    "synthdef": "ne_mod_lfo",
    "custom_params": [
        {"key": "clock_mode", "label": "CLK", "steps": 2, "default": 0.0,
         "tooltip": "CLK: sync to clock divisions\nFREE: manual frequency (0.01-100Hz)"},
        {"key": "rate", "label": "RATE", "default": 0.5,
         "tooltip": "LFO speed\nCLK: division, FREE: frequency"},
    ],
    "output_config": "waveform_phase",
    "output_labels": ["A", "B", "C", "D"],
}

# Sloth config (programmatic registration)
_MOD_GENERATOR_CONFIGS["Sloth"] = {
    "internal_id": "sloth",
    "synthdef": "ne_mod_sloth",
    "custom_params": [
        {"key": "mode", "label": "MODE", "steps": 3, "default": 0.0,
         "tooltip": "Torpor: 15-30s\nApathy: 60-90s\nInertia: 30-40min"},
    ],
    "output_config": "fixed",
    "output_labels": ["X", "Y", "Z", "R"],
}

# ARSEq+ config (programmatic registration)
_MOD_GENERATOR_CONFIGS["ARSEq+"] = {
    "internal_id": "arseq_plus",
    "synthdef": "ne_mod_arseq_plus",
    "custom_params": [
        {"key": "mode", "label": "MODE", "steps": 2, "default": 0.0,
         "tooltip": "SEQ: envelopes fire in sequence (1→2→3→4)\nPAR: all fire together"},
        {"key": "clock_mode", "label": "CLK", "steps": 2, "default": 0.0,
         "tooltip": "CLK: sync to clock divisions\nFREE: manual rate control"},
        {"key": "rate", "label": "RATE", "default": 0.364,
         "tooltip": "Envelope cycle speed\nCLK: division, FREE: frequency"},
    ],
    "output_config": "arseq_plus",
    "outputs": ["1", "2", "3", "4"],
}

# SauceOfGrav config (programmatic registration)
_MOD_GENERATOR_CONFIGS["SauceOfGrav"] = {
    "internal_id": "sauce_of_grav",
    "synthdef": "ne_mod_sauce_of_grav",
    "custom_params": [
        {"key": "clock_mode", "label": "CLK", "steps": 2, "default": 0.0,
         "tooltip": "CLK: sync to transport\nFREE: free-running"},
        {"key": "rate", "label": "RATE", "label_top": "FAST", "label_bottom": "SLOW", "default": 0.5,
         "tooltip": "Refresh event timing\nLow = slower evolution"},
        {"key": "depth", "label": "DEPTH", "label_top": "WIDE", "label_bottom": "NAR", "default": 0.5,
         "tooltip": "Hub friction\nHigh = hub loses bias faster"},
        {"key": "gravity", "label": "GRAV", "label_top": "PULL+", "label_bottom": "INDI", "default": 0.5,
         "tooltip": "Center pull strength\nLow = free drift, High = tight orbit"},
        {"key": "resonance", "label": "RESO", "label_top": "FBK+", "label_bottom": "FBK-", "default": 0.5,
         "tooltip": "Sustained motion\nHigher = more energy, prevents starvation"},
        {"key": "excursion", "label": "EXCUR", "label_top": "LOW", "label_bottom": "HI", "default": 0.5,
         "tooltip": "Range/expressiveness\nHow far outputs can travel"},
        {"key": "calm", "label_top": "WILD", "label_bottom": "CALM", "default": 0.5, "bipolar": True,
         "tooltip": "Energy macro\nCALM = tighter, WILD = bigger swings"},
    ],
    "output_config": "sauce_of_grav",
    "output_labels": ["1", "2", "3", "4"],
    "has_reset": True,
}

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


# === UNIFIED BUS TARGET KEYS ===
# Maps 1:1 with boid grid columns and unified bus indices (0-175)
# Used for boid pulse visualization to map columns to UI widgets
#
# Layout v3 (176 total - UI Refresh expansion):
# | Index     | Count | Category       | Parameters                                       |
# |-----------|-------|----------------|--------------------------------------------------|
# | 0-39      | 40    | Gen Core       | 8 slots x 5 params (freq, cutoff, res, atk, dec) |
# | 40-79     | 40    | Gen Custom     | 8 slots x 5 custom params (custom0-4)            |
# | 80-107    | 28    | Mod Slots      | 4 slots x 7 params (P0-P6)                       |
# | 108-147   | 40    | Channels       | 8 slots x 5 params (fx1, fx2, fx3, fx4, pan)     |
# | 148-167   | 20    | FX Slots       | 4 slots x 5 params (p1, p2, p3, p4, return)      |
# | 168-175   | 8     | Master Inserts | DualFilter 7 params + Heat 1 param               |

# Constants for building the target key list
GENERATOR_SLOT_COUNT = 8
CUSTOM_PARAM_COUNT = 5
MOD_PARAMS_PER_SLOT = 7  # p0-p6
CHANNEL_COUNT = 8
CHANNEL_PARAMS_COUNT = 5  # fx1, fx2, fx3, fx4, pan (v3 expansion from 3)
FX_SLOT_COUNT = 4
FX_SLOT_PARAMS_COUNT = 5  # p1, p2, p3, p4, return

def _build_unified_bus_target_keys() -> List[str]:
    """Build target key list from existing constants.

    Index == unified bus column == boid grid column.

    v3 layout (176 targets) - UI Refresh expansion:
    - Indices 0-107: UNCHANGED from v2 (gen_core, gen_custom, mod_slots)
    - Indices 108-147: Channels expanded: 8 slots x 5 params (fx1-4 + pan)
    - Indices 148-167: FX Slots: 4 slots x 5 params (p1-4 + return)
    - Indices 168-175: Master inserts (fb 7 params + heat 1 param)
    """
    keys = []

    # === INDICES 0-107: UNCHANGED FROM V2 ===

    # Gen core: slots 1-8, params freq/cutoff/res/attack/decay (indices 0-39)
    gen_params = [p['key'] for p in GENERATOR_PARAMS]  # frequency, cutoff, resonance, attack, decay
    for slot in range(1, GENERATOR_SLOT_COUNT + 1):
        for param in gen_params:
            keys.append(f"gen_{slot}_{param}")

    # Gen custom: slots 1-8, params custom0-4 (indices 40-79)
    for slot in range(1, GENERATOR_SLOT_COUNT + 1):
        for i in range(CUSTOM_PARAM_COUNT):
            keys.append(f"gen_{slot}_custom{i}")

    # Mod slots: 1-4, params p0-p6 (indices 80-107)
    for slot in range(1, MOD_SLOT_COUNT + 1):
        for i in range(MOD_PARAMS_PER_SLOT):
            keys.append(f"mod_{slot}_p{i}")

    # === INDICES 108-147: CHANNELS (v3 expansion) ===
    # 8 channels x 5 params = 40 total
    # New pattern: chan_N_fx1, chan_N_fx2, chan_N_fx3, chan_N_fx4, chan_N_pan
    for slot in range(1, CHANNEL_COUNT + 1):
        keys.append(f"chan_{slot}_fx1")
        keys.append(f"chan_{slot}_fx2")
        keys.append(f"chan_{slot}_fx3")
        keys.append(f"chan_{slot}_fx4")
        keys.append(f"chan_{slot}_pan")

    # === INDICES 148-167: FX SLOTS (v3 new) ===
    # 4 slots x 5 params = 20 total
    # Pattern: fx_slotN_p1, fx_slotN_p2, fx_slotN_p3, fx_slotN_p4, fx_slotN_return
    for slot in range(1, FX_SLOT_COUNT + 1):
        keys.append(f"fx_slot{slot}_p1")
        keys.append(f"fx_slot{slot}_p2")
        keys.append(f"fx_slot{slot}_p3")
        keys.append(f"fx_slot{slot}_p4")
        keys.append(f"fx_slot{slot}_return")

    # === INDICES 168-175: MASTER INSERTS (v3 reorganized) ===
    # DualFilter: 7 params (indices 168-174)
    keys.extend([
        "fx_fb_drive",
        "fx_fb_freq1",
        "fx_fb_reso1",
        "fx_fb_freq2",
        "fx_fb_reso2",
        "fx_fb_syncAmt",
        "fx_fb_harmonics",
    ])
    # Heat: 1 param (index 175)
    keys.append("fx_heat_drive")

    return keys

UNIFIED_BUS_TARGET_KEYS: List[str] = _build_unified_bus_target_keys()

# Validate count matches expected unified bus count (v3)
assert len(UNIFIED_BUS_TARGET_KEYS) == 176, f"Target key count mismatch: {len(UNIFIED_BUS_TARGET_KEYS)}, expected 176"

# SSOT export for any grid/matrix UI that must match unified bus layout
MOD_MATRIX_COLS = len(UNIFIED_BUS_TARGET_KEYS)


def get_target_key_for_col(col: int) -> Optional[str]:
    """Return target key for unified bus column index."""
    if 0 <= col < len(UNIFIED_BUS_TARGET_KEYS):
        return UNIFIED_BUS_TARGET_KEYS[col]
    return None


def get_col_for_target_key(key: str) -> Optional[int]:
    """Return column index for target key."""
    try:
        return UNIFIED_BUS_TARGET_KEYS.index(key)
    except ValueError:
        return None


def parse_target_key(key: str) -> Optional[Dict]:
    """
    Parse target key into components.

    Returns:
        {
            'zone': 'gen_core' | 'gen_custom' | 'mod' | 'chan' | 'fx',
            'slot': int or None,
            'param': str,
        }
    """
    if key.startswith("gen_") and "_custom" in key:
        # gen_1_custom0 -> zone='gen_custom', slot=1, param='custom0'
        parts = key.split("_")
        slot = int(parts[1])
        param = parts[2] + parts[3] if len(parts) > 3 else parts[2]
        return {'zone': 'gen_custom', 'slot': slot, 'param': param}
    elif key.startswith("gen_"):
        # gen_1_frequency -> zone='gen_core', slot=1, param='frequency'
        parts = key.split("_")
        slot = int(parts[1])
        param = parts[2]
        return {'zone': 'gen_core', 'slot': slot, 'param': param}
    elif key.startswith("mod_"):
        # mod_1_p0 -> zone='mod', slot=1, param='p0'
        parts = key.split("_")
        slot = int(parts[1])
        param = parts[2]
        return {'zone': 'mod', 'slot': slot, 'param': param}
    elif key.startswith("chan_"):
        # chan_1_echo -> zone='chan', slot=1, param='echo'
        parts = key.split("_")
        slot = int(parts[1])
        param = parts[2]
        return {'zone': 'chan', 'slot': slot, 'param': param}
    elif key.startswith("fx_slot"):
        # fx_slot1_p1 -> zone='fx_slot', slot=1, param='p1'
        # fx_slot2_return -> zone='fx_slot', slot=2, param='return'
        import re
        match = re.match(r'fx_slot(\d+)_(.+)', key)
        if match:
            slot = int(match.group(1))
            param = match.group(2)
            return {'zone': 'fx_slot', 'slot': slot, 'param': param}
        return None
    elif key.startswith("fx_"):
        # fx_fb_drive -> zone='fx_master', slot=None, param='fb_drive'
        # fx_heat_drive -> zone='fx_master', slot=None, param='heat_drive'
        param = key[3:]  # Remove 'fx_' prefix
        return {'zone': 'fx_master', 'slot': None, 'param': param}
    return None


# === FX SLOT SYSTEM (UI Refresh Phase 1) ===
# 4 swappable FX slots with generic p1-p4 parameters

FX_SLOT_TYPES = ['Empty', 'Echo', 'Reverb', 'Chorus', 'LoFi']

# Parameter labels per FX type (p1, p2, p3, p4)
FX_SLOT_PARAM_LABELS = {
    'Empty': ['--', '--', '--', '--'],
    'Echo': ['TIME', 'FDBK', 'TONE', 'WOW'],
    'Reverb': ['SIZE', 'DCAY', 'TONE', 'DAMP'],
    'Chorus': ['RATE', 'DPTH', 'MIX', 'SPRD'],
    'LoFi': ['RATE', 'BITS', 'NOIS', 'FILT'],
}

# Default parameter values per FX type
FX_SLOT_DEFAULTS = {
    'Empty': [0.5, 0.5, 0.5, 0.5],
    'Echo': [0.3, 0.3, 0.7, 0.1],
    'Reverb': [0.75, 0.65, 0.7, 0.5],
    'Chorus': [0.3, 0.5, 0.5, 0.7],
    'LoFi': [1.0, 1.0, 0.0, 0.0],
}

# Default slot assignments (slot 1-4)
FX_SLOT_DEFAULT_TYPES = ['Echo', 'Reverb', 'Chorus', 'LoFi']


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
    'gen_transpose': '/noise/gen/transpose',
    'gen_portamento': '/noise/gen/portamento',
    'gen_mute': '/noise/gen/mute',
    'gen_midi_channel': '/noise/gen/midiChannel',
    'gen_custom': '/noise/gen/custom',  # /noise/gen/custom/{slot}/{param_index}
    # Analog output stage (per-slot)
    'gen_analog_enable': '/noise/gen/analogEnable',
    'gen_analog_type': '/noise/gen/analogType',
    'gen_analog_drive': '/noise/gen/analogDrive',
    'gen_analog_mix': '/noise/gen/analogMix',
    'start_generator': '/noise/start_generator',
    'stop_generator': '/noise/stop_generator',
    'endstage_mute': '/noise/endstage/mute',  # End-stage per-slot mute (click-free)
    'fidelity_amount': '/noise/fidelity_amount',
    # Channel strip (mixer)
    'gen_volume': '/noise/gen/volume',
    'gen_strip_solo': '/noise/gen/solo',
    'gen_gain': '/noise/gen/gain',  # Per-channel gain stage (0dB, +6dB, +12dB)
    'gen_pan': '/noise/gen/pan',  # Per-channel pan (-1=L, 0=center, 1=R)
    'gen_strip_eq_base': '/noise/strip/eq',  # Per-channel EQ: /noise/strip/eq/{band}
    'gen_levels': '/noise/gen/levels',  # Per-channel level metering
    'gen_trim': '/noise/gen/trim',  # Per-channel loudness trim (from JSON config)
    'strip_echo_send': '/noise/strip/echo/send',  # Per-channel echo send (0-1) - legacy alias
    'strip_verb_send': '/noise/strip/verb/send',  # Per-channel verb send (0-1) - legacy alias
    # UI Refresh: 4 FX send buses per channel
    'strip_fx1_send': '/noise/strip/fx1/send',  # Per-channel FX1 send (0-1)
    'strip_fx2_send': '/noise/strip/fx2/send',  # Per-channel FX2 send (0-1)
    'strip_fx3_send': '/noise/strip/fx3/send',  # Per-channel FX3 send (0-1)
    'strip_fx4_send': '/noise/strip/fx4/send',  # Per-channel FX4 send (0-1)
    # UI Refresh: Configurable FX slots (4 slots)
    'fx_slot1_type': '/noise/fx/slot/1/type',
    'fx_slot1_p1': '/noise/fx/slot/1/p1',
    'fx_slot1_p2': '/noise/fx/slot/1/p2',
    'fx_slot1_p3': '/noise/fx/slot/1/p3',
    'fx_slot1_p4': '/noise/fx/slot/1/p4',
    'fx_slot1_return': '/noise/fx/slot/1/return',
    'fx_slot1_bypass': '/noise/fx/slot/1/bypass',
    'fx_slot2_type': '/noise/fx/slot/2/type',
    'fx_slot2_p1': '/noise/fx/slot/2/p1',
    'fx_slot2_p2': '/noise/fx/slot/2/p2',
    'fx_slot2_p3': '/noise/fx/slot/2/p3',
    'fx_slot2_p4': '/noise/fx/slot/2/p4',
    'fx_slot2_return': '/noise/fx/slot/2/return',
    'fx_slot2_bypass': '/noise/fx/slot/2/bypass',
    'fx_slot3_type': '/noise/fx/slot/3/type',
    'fx_slot3_p1': '/noise/fx/slot/3/p1',
    'fx_slot3_p2': '/noise/fx/slot/3/p2',
    'fx_slot3_p3': '/noise/fx/slot/3/p3',
    'fx_slot3_p4': '/noise/fx/slot/3/p4',
    'fx_slot3_return': '/noise/fx/slot/3/return',
    'fx_slot3_bypass': '/noise/fx/slot/3/bypass',
    'fx_slot4_type': '/noise/fx/slot/4/type',
    'fx_slot4_p1': '/noise/fx/slot/4/p1',
    'fx_slot4_p2': '/noise/fx/slot/4/p2',
    'fx_slot4_p3': '/noise/fx/slot/4/p3',
    'fx_slot4_p4': '/noise/fx/slot/4/p4',
    'fx_slot4_return': '/noise/fx/slot/4/return',
    'fx_slot4_bypass': '/noise/fx/slot/4/bypass',
    'master_echo_return': '/noise/master/echo/return',  # Master echo return level
    'master_verb_return': '/noise/master/verb/return',  # Master verb return level
    # Heat (saturation)
    'heat_circuit': '/noise/master/heat/circuit',  # 0=Clean, 1=Tape, 2=Tube, 3=Crunch
    'heat_drive': '/noise/master/heat/drive',  # 0-1
    'heat_mix': '/noise/master/heat/mix',  # 0-1 wet/dry
    'heat_bypass': '/noise/master/heat/bypass',  # 0=on, 1=bypassed
    # Tape Echo (delay)
    'echo_time': '/noise/master/echo/time',  # 0-1 (maps to 50-500ms)
    'echo_feedback': '/noise/master/echo/feedback',  # 0-1
    'echo_tone': '/noise/master/echo/tone',  # 0-1 (HF loss)
    'echo_wow': '/noise/master/echo/wow',  # 0-1 (flutter)
    'echo_spring': '/noise/master/echo/spring',  # 0-1 (spring reverb)
    'echo_verb_send': '/noise/master/echo/verb_send',  # 0-1 (cross-feed to reverb)
    # Reverb
    'verb_size': '/noise/master/verb/size',  # 0-1 room size
    'verb_decay': '/noise/master/verb/decay',  # 0-1 tail length
    'verb_tone': '/noise/master/verb/tone',  # 0-1 brightness
    # Dual Filter
    'fb_drive': '/noise/master/fb/drive',  # 0-1
    'fb_freq1': '/noise/master/fb/freq1',  # 0-1 (20Hz-20kHz exp)
    'fb_reso1': '/noise/master/fb/reso1',  # 0-1
    'fb_mode1': '/noise/master/fb/mode1',  # 0=LP, 1=BP, 2=HP
    'fb_sync1': '/noise/master/fb/sync1',  # "" (free) or rate string (/16, CLK, x2, etc)
    'fb_freq2': '/noise/master/fb/freq2',  # 0-1 (20Hz-20kHz exp)
    'fb_reso2': '/noise/master/fb/reso2',  # 0-1
    'fb_mode2': '/noise/master/fb/mode2',  # 0=LP, 1=BP, 2=HP
    'fb_sync2': '/noise/master/fb/sync2',  # "" (free) or rate string (/16, CLK, x2, etc)
    'fb_sync_amt': '/noise/master/fb/syncAmt',  # 0-1 sync modulation depth
    'fb_harmonics': '/noise/master/fb/harmonics',  # 0=Free, 1-7=sync ratios
    'fb_routing': '/noise/master/fb/routing',  # 0=Serial, 1=Parallel
    'fb_mix': '/noise/master/fb/mix',  # 0-1 wet/dry
    'fb_bypass': '/noise/master/fb/bypass',  # 0=on, 1=bypassed
    # MIDI
    'midi_device': '/noise/midi/device',
    'midi_gate': '/noise/midi/gate',  # SC -> Python for LED flash
    'midi_cc': '/noise/midi/cc',  # SC -> Python for CC mapping
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
    'mod_values': '/noise/mod/values',
    'mod_scope_enable': '/noise/mod/scope/enable',  # /noise/mod/scope/enable/{slot} (Python → SC)
    
    # Mod routing (DEPRECATED - generator routes now use unified bus_route_* paths)
    # Legacy paths kept for extended mod routes which still use extmod_* paths
    'mod_route_add': '/noise/mod/route/add',        # DEPRECATED - use bus_route_set
    'mod_route_set': '/noise/mod/route/set',        # DEPRECATED - use bus_route_set
    'mod_route_remove': '/noise/mod/route/remove',  # DEPRECATED - use bus_route_remove
    'mod_route_clear_all': '/noise/mod/route/clear_all',  # DEPRECATED - use bus_route_clear
    # Extended modulation (mod matrix expansion)
    'extmod_add_route': '/noise/extmod/add_route',
    'extmod_remove_route': '/noise/extmod/remove_route',
    'extmod_set_user_param': '/noise/extmod/set_user_param',
    'extmod_clear_all': '/noise/extmod/clear_all',
    'extmod_values': '/noise/extmod/values',  # SC → Python: extended mod value stream

    # === BUS UNIFICATION ===
    # Mod slot parameters (P0-P6 per slot)
    'bus_mod_p0': '/noise/mod/bus/p0',  # [slot, value]
    'bus_mod_p1': '/noise/mod/bus/p1',
    'bus_mod_p2': '/noise/mod/bus/p2',
    'bus_mod_p3': '/noise/mod/bus/p3',
    'bus_mod_p4': '/noise/mod/bus/p4',
    'bus_mod_p5': '/noise/mod/bus/p5',
    'bus_mod_p6': '/noise/mod/bus/p6',
    # Channel parameters
    'bus_chan_echo': '/noise/channel/bus/echoSend',  # [channel, value]
    'bus_chan_verb': '/noise/channel/bus/verbSend',
    'bus_chan_pan': '/noise/channel/bus/pan',
    # FX: Heat
    'bus_heat_drive': '/noise/fx/bus/heat/drive',  # [value]
    # NOTE: bus_heat_mix removed - mix is manual-only via 'heat_mix' path
    # FX: Echo
    'bus_echo_time': '/noise/fx/bus/echo/time',
    'bus_echo_feedback': '/noise/fx/bus/echo/feedback',
    'bus_echo_tone': '/noise/fx/bus/echo/tone',
    'bus_echo_wow': '/noise/fx/bus/echo/wow',
    'bus_echo_spring': '/noise/fx/bus/echo/spring',
    'bus_echo_verb_send': '/noise/fx/bus/echo/verbSend',
    # FX: Reverb
    'bus_verb_size': '/noise/fx/bus/reverb/size',
    'bus_verb_decay': '/noise/fx/bus/reverb/decay',
    'bus_verb_tone': '/noise/fx/bus/reverb/tone',
    # FX: Dual Filter
    'bus_fb_drive': '/noise/fx/bus/fb/drive',
    'bus_fb_freq1': '/noise/fx/bus/fb/freq1',
    'bus_fb_freq2': '/noise/fx/bus/fb/freq2',
    'bus_fb_reso1': '/noise/fx/bus/fb/reso1',
    'bus_fb_reso2': '/noise/fx/bus/fb/reso2',
    'bus_fb_sync_amt': '/noise/fx/bus/fb/syncAmt',
    'bus_fb_harmonics': '/noise/fx/bus/fb/harmonics',
    # NOTE: bus_fb_mix removed - mix is manual-only via 'fb_mix' path
    # Route operations
    'bus_route_set': '/noise/bus/route/set',  # [sourceKey, targetKey, depth, amount, offset, polarity, invert]
    'bus_route_remove': '/noise/bus/route/remove',  # [sourceKey, targetKey]
    'bus_route_clear': '/noise/bus/route/clear',  # [targetKey] or no args for clear all
    # Boid operations (spec v4)
    'boid_enable': '/noise/boid/enable',  # [int enabled] - 1=enable, 0=disable
    'boid_offsets': '/noise/boid/offsets',  # [busIndex1, offset1, busIndex2, offset2, ...]
    'boid_clear': '/noise/boid/clear',  # no args - clear all offsets
    # Value stream (SC → Python)
    'bus_values': '/noise/bus/values',  # [targetKey1, value1, ...]
    # Scope tap
    'scope_slot': '/noise/scope/slot',          # [slot] 0-7
    'scope_threshold': '/noise/scope/threshold', # [float] -1.0 to 1.0
    'scope_freeze': '/noise/scope/freeze',       # [int] 0=live, 1=frozen
    'scope_enable': '/noise/scope/enable',       # [int] 0=off, 1=on
    'scope_data': '/noise/scope/data',           # SC → Python: [float, float, ...] waveform
    'scope_debug': '/noise/scope/debug',         # Python → SC: trigger debug capture
    'scope_debug_done': '/noise/scope/debug/done', # SC → Python: [path, write_pos] capture complete
    # Telemetry (development tool)
    'telem_enable': '/noise/telem/enable',             # [slot, rate] Python → SC
    'telem_tap_enable': '/noise/telem/tap/enable',     # [slot, rate, calGain] Python → SC: internal tap
    'telem_gen': '/noise/telem/gen',                   # SC → Python: control-rate data
    'telem_wave_enable': '/noise/telem/wave/enable',   # [slot, enable] Python → SC
    'telem_wave': '/noise/telem/wave',                 # SC → Python: waveform samples
    'telem_source': '/noise/telem/source',             # [slot, source_id] Python → SC: select tap point
}

# === TELEMETRY SOURCE POINTS ===
TELEM_SOURCES = ["Pre-Analog", "Post-Analog", "Post-Endstage"]
TELEM_SOURCE_INDEX = {name: i for i, name in enumerate(TELEM_SOURCES)}

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
