"""
Boid State - Data model for boid modulation preset state

Handles serialization/deserialization for preset save/load.
Includes zone filtering state (GEN/MOD/CHN toggles).
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Set
import random


DEFAULT_BOID_COUNT = 8


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
    zone_fx: bool = True     # Columns 132-150 (FX params)

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
            ranges.append((132, 150))
        return ranges

    def is_column_allowed(self, col: int) -> bool:
        """Check if a column is within an allowed zone."""
        if self.zone_gen and 0 <= col <= 79:
            return True
        if self.zone_mod and 80 <= col <= 107:
            return True
        if self.zone_chan and 108 <= col <= 131:
            return True
        if self.zone_fx and 132 <= col <= 150:
            return True
        return False


def generate_random_seed() -> int:
    """Generate a random seed value."""
    return random.randint(0, 0x7FFFFFFF)
