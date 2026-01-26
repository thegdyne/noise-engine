"""
Immutable Historical Target Keys - v2 (149 targets)

This file contains the FROZEN v2 key list for boid preset migration.
These keys represent the bus unification layout before the UI refresh expansion.

DO NOT MODIFY THIS FILE - it serves as a reference for migrating old presets
that store column indices. Migration should map old indices to new indices
using key names as the stable identifier.

Layout (v2 - 149 total):
| Index     | Count | Category      | Parameters                                      |
|-----------|-------|---------------|------------------------------------------------|
| 0-39      | 40    | Gen Core      | 8 slots x 5 params (freq, cutoff, res, atk, dec)|
| 40-79     | 40    | Gen Custom    | 8 slots x 5 custom params (custom0-4)          |
| 80-107    | 28    | Mod Slots     | 4 slots x 7 params (P0-P6)                     |
| 108-131   | 24    | Channels      | 8 slots x 3 params (echo, verb, pan)           |
| 132-148   | 17    | FX            | Heat, Echo, Reverb, DualFilter (mix excluded)  |
"""

from typing import List


def _build_v2_keys() -> List[str]:
    """Build the v2 (149) target key list - FROZEN, do not modify."""
    keys = []

    # Gen core: slots 1-8, params freq/cutoff/res/attack/decay (indices 0-39)
    gen_params = ['frequency', 'cutoff', 'resonance', 'attack', 'decay']
    for slot in range(1, 9):
        for param in gen_params:
            keys.append(f"gen_{slot}_{param}")

    # Gen custom: slots 1-8, params custom0-4 (indices 40-79)
    for slot in range(1, 9):
        for i in range(5):
            keys.append(f"gen_{slot}_custom{i}")

    # Mod slots: 1-4, params p0-p6 (indices 80-107)
    for slot in range(1, 5):
        for i in range(7):
            keys.append(f"mod_{slot}_p{i}")

    # Channels: 1-8, params echo/verb/pan (indices 108-131)
    for slot in range(1, 9):
        for param in ['echo', 'verb', 'pan']:
            keys.append(f"chan_{slot}_{param}")

    # FX (indices 132-148) - must match SC bus_unification.scd order exactly
    keys.extend([
        "fx_heat_drive",
        "fx_echo_time", "fx_echo_feedback", "fx_echo_tone",
        "fx_echo_wow", "fx_echo_spring", "fx_echo_verbSend",
        "fx_verb_size", "fx_verb_decay", "fx_verb_tone",
        "fx_fb_drive", "fx_fb_freq1", "fx_fb_freq2",
        "fx_fb_reso1", "fx_fb_reso2", "fx_fb_syncAmt", "fx_fb_harmonics",
    ])

    return keys


# The frozen v2 key list
TARGET_KEYS_V2: List[str] = _build_v2_keys()

# Validate count on module load
assert len(TARGET_KEYS_V2) == 149, f"TARGET_KEYS_V2 count mismatch: {len(TARGET_KEYS_V2)}, expected 149"
