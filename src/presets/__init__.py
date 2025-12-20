"""
Presets module - save/load patch state.
"""

from .preset_schema import (
    PresetState,
    SlotState,
    ChannelState,
    MixerState,
    validate_preset,
    PRESET_VERSION,
)

from .preset_manager import (
    PresetManager,
    PresetError,
    collect_state,
    apply_state,
)

__all__ = [
    "PresetState",
    "SlotState", 
    "ChannelState",
    "MixerState",
    "validate_preset",
    "PRESET_VERSION",
    "PresetManager",
    "PresetError",
    "collect_state",
    "apply_state",
]
