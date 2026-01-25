"""
Boid State - Data model for boid modulation preset state

Handles serialization/deserialization for preset save/load.
Includes zone filtering (columns) and row filtering (source rows).
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List
import random


DEFAULT_BOID_COUNT = 8

# Behavior presets: (dispersion, energy, fade)
BEHAVIOR_PRESETS = {
    'custom': None,  # User-defined values
    'swarm': (0.2, 0.5, 0.3),   # High cohesion, medium speed, short fade
    'scatter': (0.9, 0.8, 0.5), # High dispersion, high energy, medium fade
    'drift': (0.3, 0.2, 0.8),   # Low energy, low dispersion, long fade
    'chaos': (0.7, 0.9, 0.4),   # High everything
}

# Row ranges for mod slots (4 outputs each)
ROW_RANGES = {
    'all': (0, 15),      # All 16 rows
    'slot1': (0, 3),     # Mod slot 1 outputs
    'slot2': (4, 7),     # Mod slot 2 outputs
    'slot3': (8, 11),    # Mod slot 3 outputs
    'slot4': (12, 15),   # Mod slot 4 outputs
}


@dataclass
class BoidState:
    """
    Persistent state for boid modulation layer.

    Stored in presets and restored on load.
    """

    # Parameters (normalized 0-1)
    dispersion: float = 0.5
    energy: float = 0.5
    fade: float = 0.5
    depth: float = 1.0

    # Boid count
    boid_count: int = DEFAULT_BOID_COUNT

    # Seed state
    seed: int = 0
    seed_locked: bool = False

    # Zone filtering (which target zones boids can reach)
    # MOD zone OFF by default to avoid the UI overwrite issue
    zone_gen: bool = True    # Columns 0-79 (generator params)
    zone_mod: bool = False   # Columns 80-107 (mod slot params) - OFF by default!
    zone_chan: bool = True   # Columns 108-131 (channel params)
    zone_fx: bool = True     # Columns 132-148 (FX params)

    # Row filtering (which source rows boids can use)
    # Each slot has 4 outputs, so 16 total rows
    row_slot1: bool = True   # Rows 0-3 (mod slot 1 outputs)
    row_slot2: bool = True   # Rows 4-7 (mod slot 2 outputs)
    row_slot3: bool = True   # Rows 8-11 (mod slot 3 outputs)
    row_slot4: bool = True   # Rows 12-15 (mod slot 4 outputs)

    # Behavior preset (custom = user values)
    behavior_preset: str = 'custom'

    # Enabled state
    enabled: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for preset saving."""
        return {
            "dispersion": self.dispersion,
            "energy": self.energy,
            "fade": self.fade,
            "depth": self.depth,
            "boid_count": self.boid_count,
            "seed": self.seed,
            "seed_locked": self.seed_locked,
            "zone_gen": self.zone_gen,
            "zone_mod": self.zone_mod,
            "zone_chan": self.zone_chan,
            "zone_fx": self.zone_fx,
            "row_slot1": self.row_slot1,
            "row_slot2": self.row_slot2,
            "row_slot3": self.row_slot3,
            "row_slot4": self.row_slot4,
            "behavior_preset": self.behavior_preset,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BoidState":
        """Deserialize from preset data."""
        # Handle legacy 'sensitivity' key
        fade = data.get("fade", data.get("sensitivity", 0.5))

        return cls(
            dispersion=float(data.get("dispersion", 0.5)),
            energy=float(data.get("energy", 0.5)),
            fade=float(fade),
            depth=float(data.get("depth", 1.0)),
            boid_count=int(data.get("boid_count", DEFAULT_BOID_COUNT)),
            seed=int(data.get("seed", 0)),
            seed_locked=bool(data.get("seed_locked", False)),
            zone_gen=bool(data.get("zone_gen", True)),
            zone_mod=bool(data.get("zone_mod", False)),  # Default OFF
            zone_chan=bool(data.get("zone_chan", True)),
            zone_fx=bool(data.get("zone_fx", True)),
            row_slot1=bool(data.get("row_slot1", True)),
            row_slot2=bool(data.get("row_slot2", True)),
            row_slot3=bool(data.get("row_slot3", True)),
            row_slot4=bool(data.get("row_slot4", True)),
            behavior_preset=str(data.get("behavior_preset", "custom")),
            enabled=bool(data.get("enabled", False)),
        )

    def get_active_seed(self) -> int:
        """
        Get the seed to use for simulation.

        If seed_locked, returns stored seed.
        Otherwise, generates and stores a new random seed.
        """
        if self.seed_locked:
            return self.seed
        else:
            self.seed = random.randint(0, 0x7FFFFFFF)
            return self.seed

    def get_allowed_column_ranges(self) -> list:
        """
        Get list of (start, end) column ranges based on zone toggles.

        Returns list of tuples for enabled zones.
        """
        ranges = []
        if self.zone_gen:
            ranges.append((0, 79))
        if self.zone_mod:
            ranges.append((80, 107))
        if self.zone_chan:
            ranges.append((108, 131))
        if self.zone_fx:
            ranges.append((132, 148))
        return ranges

    def is_column_allowed(self, col: int) -> bool:
        """Check if a column is within an allowed zone."""
        if self.zone_gen and 0 <= col <= 79:
            return True
        if self.zone_mod and 80 <= col <= 107:
            return True
        if self.zone_chan and 108 <= col <= 131:
            return True
        if self.zone_fx and 132 <= col <= 148:
            return True
        return False

    def is_row_allowed(self, row: int) -> bool:
        """Check if a row is within an allowed slot range."""
        if self.row_slot1 and 0 <= row <= 3:
            return True
        if self.row_slot2 and 4 <= row <= 7:
            return True
        if self.row_slot3 and 8 <= row <= 11:
            return True
        if self.row_slot4 and 12 <= row <= 15:
            return True
        return False

    def is_cell_allowed(self, row: int, col: int) -> bool:
        """Check if a cell (row, col) is allowed by both row and column filters."""
        return self.is_row_allowed(row) and self.is_column_allowed(col)

    def apply_behavior_preset(self, preset_name: str) -> bool:
        """
        Apply a behavior preset, setting dispersion/energy/fade.

        Returns True if preset was applied, False if invalid preset.
        """
        if preset_name not in BEHAVIOR_PRESETS:
            return False

        if preset_name == 'custom':
            self.behavior_preset = 'custom'
            return True

        values = BEHAVIOR_PRESETS[preset_name]
        if values:
            self.dispersion, self.energy, self.fade = values
            self.behavior_preset = preset_name
        return True

    def get_preset_names(self) -> List[str]:
        """Get list of available preset names."""
        return list(BEHAVIOR_PRESETS.keys())


def generate_random_seed() -> int:
    """Generate a random seed value."""
    return random.randint(0, 0x7FFFFFFF)
