"""
Boid Target Scales - Loads and applies per-category scaling for boid modulation.

Scaling is applied Python-side before sending offsets to SC.
SC receives pre-scaled offsets and applies them directly.
"""

import json
import os
from typing import Dict, Optional

# Default scales (used if config file not found)
DEFAULT_SCALES = {
    "generator_core": {
        "freq": 0.3,
        "cutoff": 0.4,
        "res": 0.3,
        "attack": 0.3,
        "decay": 0.3,
    },
    "generator_custom": {
        "custom0": 0.4,
        "custom1": 0.4,
        "custom2": 0.4,
        "custom3": 0.4,
        "custom4": 0.4,
    },
    "mod_slots": {
        "p0": 0.4,
        "p1": 0.5,
        "p2": 0.5,
        "p3": 0.5,
        "p4": 0.5,
        "p5": 0.5,
        "p6": 0.5,
    },
    "channels": {
        "fx1": 0.4,
        "fx2": 0.4,
        "fx3": 0.4,
        "fx4": 0.4,
        "pan": 0.6,
    },
    "fx_slots": {
        "p1": 0.5,
        "p2": 0.5,
        "p3": 0.5,
        "p4": 0.5,
        "return": 0.4,
    },
    "fx_dualFilter": {
        "drive": 0.5,
        "freq1": 0.6,
        "reso1": 0.4,
        "freq2": 0.6,
        "reso2": 0.4,
        "syncAmt": 0.5,
        "harmonics": 0.5,
    },
    "fx_heat": {
        "drive": 0.5,
    },
}


class BoidScales:
    """Manages boid target scaling configuration."""

    def __init__(self, config_path: Optional[str] = None):
        self._config_path = config_path or "config/boid_target_scales.json"
        self._scales_by_index: Dict[int, float] = {}
        self._raw_config: dict = {}
        self._build_index_map(DEFAULT_SCALES)
        self.reload()

    def reload(self) -> bool:
        """
        Reload scales from config file.

        Returns:
            True if loaded successfully, False if using defaults.
        """
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, 'r') as f:
                    data = json.load(f)
                self._raw_config = data
                self._build_index_map(data)
                return True
            except (json.JSONDecodeError, IOError) as e:
                print(f"WARNING: Failed to load boid scales: {e}")
                return False
        return False

    def _build_index_map(self, data: dict) -> None:
        """Build target_index -> scale lookup from config data."""
        scales = {}

        # Generator core (indices 0-39: 8 slots x 5 params)
        gen_core = data.get("generator_core", {})
        param_order = ["freq", "cutoff", "res", "attack", "decay"]
        for slot in range(8):
            base = slot * 5
            for param_idx, param in enumerate(param_order):
                scales[base + param_idx] = float(gen_core.get(param, 0.5))

        # Generator custom (indices 40-79: 8 slots x 5 custom)
        gen_custom = data.get("generator_custom", {})
        for slot in range(8):
            base = 40 + slot * 5
            for custom_idx in range(5):
                key = f"custom{custom_idx}"
                scales[base + custom_idx] = float(gen_custom.get(key, 0.5))

        # Mod slots (indices 80-107: 4 slots x 7 params)
        mod_slots = data.get("mod_slots", {})
        for slot in range(4):
            base = 80 + slot * 7
            for p_idx in range(7):
                key = f"p{p_idx}"
                scales[base + p_idx] = float(mod_slots.get(key, 0.5))

        # Channels (indices 108-147: 8 channels x 5 params - v3 layout)
        channels = data.get("channels", {})
        chan_params = ["fx1", "fx2", "fx3", "fx4", "pan"]
        for chan in range(8):
            base = 108 + chan * 5
            for param_idx, param in enumerate(chan_params):
                scales[base + param_idx] = float(channels.get(param, 0.5))

        # FX Slots (indices 148-167: 4 slots x 5 params - v3 new)
        fx_slots = data.get("fx_slots", {})
        slot_params = ["p1", "p2", "p3", "p4", "return"]
        for slot in range(4):
            base = 148 + slot * 5
            for param_idx, param in enumerate(slot_params):
                scales[base + param_idx] = float(fx_slots.get(param, 0.5))

        # FX DualFilter (indices 168-174: 7 params)
        fx_df = data.get("fx_dualFilter", {})
        df_params = ["drive", "freq1", "reso1", "freq2", "reso2", "syncAmt", "harmonics"]
        for idx, param in enumerate(df_params):
            scales[168 + idx] = float(fx_df.get(param, 0.5))

        # FX Heat (index 175)
        fx_heat = data.get("fx_heat", {})
        scales[175] = float(fx_heat.get("drive", 0.5))

        self._scales_by_index = scales

    def get_scale(self, target_index: int) -> float:
        """
        Get scale factor for a target index.

        Args:
            target_index: Target index 0-175

        Returns:
            Scale factor (defaults to 1.0 if not found)
        """
        return self._scales_by_index.get(target_index, 1.0)

    def apply_scale(self, target_index: int, offset: float) -> float:
        """
        Apply scaling to a raw boid offset.

        Args:
            target_index: Target index 0-175
            offset: Raw boid offset value

        Returns:
            Scaled offset
        """
        return offset * self.get_scale(target_index)

    def scale_snapshot(self, snapshot: Dict[int, float]) -> Dict[int, float]:
        """
        Apply scaling to an entire offset snapshot.

        Args:
            snapshot: Dict mapping target_index -> raw_offset

        Returns:
            Dict mapping target_index -> scaled_offset
        """
        return {
            idx: self.apply_scale(idx, offset)
            for idx, offset in snapshot.items()
        }


# Global instance
_boid_scales: Optional[BoidScales] = None


def get_boid_scales() -> BoidScales:
    """Get the global BoidScales instance (lazy init)."""
    global _boid_scales
    if _boid_scales is None:
        _boid_scales = BoidScales()
    return _boid_scales


def reload_boid_scales() -> bool:
    """Reload the global boid scales from config file."""
    return get_boid_scales().reload()
