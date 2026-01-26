"""
Preset Migrations - Bus Unification v2 to v3

Handles migration of boid presets that store column indices.
The v3 bus layout expands from 149 to 176 targets, with indices 108+
remapped to a new layout.

Key changes from v2 to v3:
- Indices 0-107: UNCHANGED (gen_core, gen_custom, mod_slots)
- Indices 108-131 (v2 channels) -> 108-147 (v3 channels expanded)
- Indices 132-148 (v2 FX) -> 148-175 (v3 FX slots + master inserts)
"""

from typing import Dict, List, Optional


# ============================================================================
# KEY_ALIAS: Maps old v2 keys to new v3 keys
# ============================================================================
# This mapping allows presets using key names (rather than indices) to be
# transparently migrated. Keys that didn't change are not included.

KEY_ALIAS: Dict[str, str] = {
    # Channel mappings (v2 echo/verb -> v3 fx1/fx2)
    # v2 had 3 params per channel: echo, verb, pan
    # v3 has 5 params per channel: fx1, fx2, fx3, fx4, pan
    'chan_1_echo': 'chan_1_fx1',
    'chan_1_verb': 'chan_1_fx2',
    'chan_2_echo': 'chan_2_fx1',
    'chan_2_verb': 'chan_2_fx2',
    'chan_3_echo': 'chan_3_fx1',
    'chan_3_verb': 'chan_3_fx2',
    'chan_4_echo': 'chan_4_fx1',
    'chan_4_verb': 'chan_4_fx2',
    'chan_5_echo': 'chan_5_fx1',
    'chan_5_verb': 'chan_5_fx2',
    'chan_6_echo': 'chan_6_fx1',
    'chan_6_verb': 'chan_6_fx2',
    'chan_7_echo': 'chan_7_fx1',
    'chan_7_verb': 'chan_7_fx2',
    'chan_8_echo': 'chan_8_fx1',
    'chan_8_verb': 'chan_8_fx2',

    # Old FX keys -> New FX slot or master insert keys
    # v2 had specific FX (echo, reverb, dualfilter, heat)
    # v3 has generic FX slots + master inserts
    # These mappings are suggestions - actual routing depends on FX slot configuration
    'fx_echo_time': 'fx_slot1_p1',
    'fx_echo_feedback': 'fx_slot1_p2',
    'fx_echo_tone': 'fx_slot1_p3',
    'fx_echo_wow': 'fx_slot1_p4',
    'fx_echo_spring': 'fx_slot2_p1',  # Overflow to slot 2
    'fx_echo_verbSend': 'fx_slot2_p2',

    'fx_verb_size': 'fx_slot2_p3',
    'fx_verb_decay': 'fx_slot2_p4',
    'fx_verb_tone': 'fx_slot2_return',

    # DualFilter keys stay as master inserts
    # (already named fx_fb_* so no key change needed)
    # Heat key stays as master insert
    # (already named fx_heat_* so no key change needed)
}


# ============================================================================
# INDEX REMAPPING: v2 index -> v3 index
# ============================================================================
# For indices 108+, the layout changed. This provides direct index mapping.

def _build_v2_to_v3_index_map() -> Dict[int, int]:
    """Build mapping from v2 indices to v3 indices.

    Indices 0-107 are unchanged.
    Indices 108+ need remapping based on the layout change.
    """
    mapping = {}

    # 0-107: Identity mapping (unchanged)
    for i in range(108):
        mapping[i] = i

    # 108-131 (v2 channels): 8 channels x 3 params (echo, verb, pan)
    # -> 108-147 (v3 channels): 8 channels x 5 params (fx1, fx2, fx3, fx4, pan)
    # v2 channel param order: echo(0), verb(1), pan(2)
    # v3 channel param order: fx1(0), fx2(1), fx3(2), fx4(3), pan(4)
    for chan in range(8):
        v2_base = 108 + (chan * 3)
        v3_base = 108 + (chan * 5)

        # echo -> fx1
        mapping[v2_base + 0] = v3_base + 0
        # verb -> fx2
        mapping[v2_base + 1] = v3_base + 1
        # pan -> pan (index 2 -> 4)
        mapping[v2_base + 2] = v3_base + 4

    # 132-148 (v2 FX): 17 params
    # -> 148-175 (v3 master inserts + may need FX slot mapping)
    # v2 FX layout:
    #   132: fx_heat_drive
    #   133-138: fx_echo_* (6 params)
    #   139-141: fx_verb_* (3 params)
    #   142-148: fx_fb_* (7 params)

    # For v3, master inserts are at 168-175:
    #   168-174: fx_fb_* (7 params)
    #   175: fx_heat_drive

    # Map v2 heat (132) -> v3 heat (175)
    mapping[132] = 175

    # Map v2 echo (133-138) -> v3 fx_slot1/2 (148-157)
    # This is approximate - actual mapping depends on FX slot configuration
    mapping[133] = 148  # time -> slot1_p1
    mapping[134] = 149  # feedback -> slot1_p2
    mapping[135] = 150  # tone -> slot1_p3
    mapping[136] = 151  # wow -> slot1_p4
    mapping[137] = 153  # spring -> slot2_p1
    mapping[138] = 154  # verbSend -> slot2_p2

    # Map v2 reverb (139-141) -> v3 fx_slot2 (155-157)
    mapping[139] = 155  # size -> slot2_p3
    mapping[140] = 156  # decay -> slot2_p4
    mapping[141] = 157  # tone -> slot2_return

    # Map v2 dualfilter (142-148) -> v3 master insert (168-174)
    mapping[142] = 168  # fx_fb_drive
    mapping[143] = 169  # fx_fb_freq1
    mapping[144] = 171  # fx_fb_freq2 (note: order changed in v3)
    mapping[145] = 170  # fx_fb_reso1 (note: order changed in v3)
    mapping[146] = 172  # fx_fb_reso2
    mapping[147] = 173  # fx_fb_syncAmt
    mapping[148] = 174  # fx_fb_harmonics

    return mapping


V2_TO_V3_INDEX_MAP: Dict[int, int] = _build_v2_to_v3_index_map()


# ============================================================================
# MIGRATION FUNCTIONS
# ============================================================================

def migrate_boid_columns(old_cols: List[int]) -> List[int]:
    """Migrate a list of v2 column indices to v3 indices.

    Args:
        old_cols: List of v2 column indices (0-148)

    Returns:
        List of v3 column indices (0-175)

    Indices that cannot be mapped are dropped with a warning.
    """
    new_cols = []
    for col in old_cols:
        if col in V2_TO_V3_INDEX_MAP:
            new_cols.append(V2_TO_V3_INDEX_MAP[col])
        else:
            # Unknown index - skip it
            print(f"Warning: Cannot migrate column index {col}, skipping")
    return new_cols


def migrate_key(old_key: str) -> str:
    """Migrate a v2 key name to v3 key name.

    Args:
        old_key: v2 key name

    Returns:
        v3 key name (or original if no mapping needed)
    """
    return KEY_ALIAS.get(old_key, old_key)


def get_v3_index_for_v2_key(v2_key: str) -> Optional[int]:
    """Get the v3 index for a v2 key name.

    Args:
        v2_key: v2 key name

    Returns:
        v3 index, or None if key is unknown
    """
    from src.config.target_keys_v2 import TARGET_KEYS_V2
    from src.config import UNIFIED_BUS_TARGET_KEYS

    # First, get the v2 index
    try:
        v2_index = TARGET_KEYS_V2.index(v2_key)
    except ValueError:
        return None

    # Then map to v3 index
    v3_index = V2_TO_V3_INDEX_MAP.get(v2_index)
    if v3_index is None:
        return None

    # Verify the v3 index is valid
    if 0 <= v3_index < len(UNIFIED_BUS_TARGET_KEYS):
        return v3_index

    return None


def is_v2_preset(preset_data: dict) -> bool:
    """Check if a preset was saved with v2 layout.

    Args:
        preset_data: Preset dictionary

    Returns:
        True if preset uses v2 layout
    """
    # Check for v2 indicators:
    # 1. No version field or version < 3
    # 2. Has old key names like chan_N_echo
    version = preset_data.get('version', 1)
    if version < 3:
        return True

    # Check for v2 key names in boid zones or routes
    boid_data = preset_data.get('boid', {})
    if any(key in str(boid_data) for key in ['_echo', '_verb', 'fx_echo_', 'fx_verb_']):
        return True

    return False
