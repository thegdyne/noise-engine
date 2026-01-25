"""
Boid Bus Integration - Grid to Bus Mapping and OSC Protocol

Implements the boid bus integration spec v4 (updated for 149-bus layout):
- Grid to bus mapping for unified buses (columns 0-148 -> bus indices base+0 to base+148)
- Aggregation of boid contributions per bus index
- Deterministic downselection (max 100 entries)
- Non-finite value filtering
- Single-snapshot-per-tick OSC sending

Bus Layout (149 total, contiguous indices):
| Index     | Count | Category      | Parameters                                      |
|-----------|-------|---------------|------------------------------------------------|
| 0-39      | 40    | Gen Core      | 8 slots x 5 params (freq, cutoff, res, atk, dec)|
| 40-79     | 40    | Gen Custom    | 8 slots x 5 custom params (custom0-4)          |
| 80-107    | 28    | Mod Slots     | 4 slots x 7 params (P0-P6)                     |
| 108-131   | 24    | Channels      | 8 slots x 3 params (echo, verb, pan)           |
| 132-148   | 17    | FX            | Heat, Echo, Reverb, DualFilter (mix excluded)  |
"""

from typing import Dict, List, Optional, Tuple
import math


# Grid layout constants per spec (149-bus layout)
GRID_TOTAL_COLUMNS = 149  # 0..148

# Column ranges (directly map to unified bus indices)
GEN_CORE_COLS = (0, 39)       # 40 cols -> 8 slots x 5 core params
GEN_CUSTOM_COLS = (40, 79)    # 40 cols -> 8 slots x 5 custom params
MOD_SLOT_COLS = (80, 107)     # 28 cols -> 4 slots x 7 params
CHANNEL_COLS = (108, 131)     # 24 cols -> 8 channels x 3 params
FX_COLS = (132, 148)          # 17 cols -> FX params (mix excluded)

# Unified bus index range
# NOTE: SC allocates dynamically - the actual base is queried at connect time
# Default fallback is 1000 but will be updated via set_unified_bus_base()
_DEFAULT_BUS_BASE = 1000
_unified_bus_base = _DEFAULT_BUS_BASE  # Updated by set_unified_bus_base()

# Protocol constraints
MAX_OFFSET_PAIRS = 100


def get_unified_bus_base() -> int:
    """Get the current unified bus base (updated from SC at connect time)."""
    return _unified_bus_base


def set_unified_bus_base(base: int) -> None:
    """Set the unified bus base (called when SC reports its allocation)."""
    global _unified_bus_base
    _unified_bus_base = base


def grid_to_bus(row: int, col: int) -> Optional[int]:
    """
    Map grid coordinates to unified bus index.

    Args:
        row: Grid row (not used in this phase, included for future compatibility)
        col: Grid column (0-148)

    Returns:
        Bus index for unified buses (direct 1:1 mapping now that gens are unified)

    Layout (relative to bus base):
    - col 0-39: bus base+0 to base+39 (gen core params)
    - col 40-79: bus base+40 to base+79 (gen custom params)
    - col 80-107: bus base+80 to base+107 (mod slot params)
    - col 108-131: bus base+108 to base+131 (channel params)
    - col 132-148: bus base+132 to base+148 (FX params)
    """
    if 0 <= col < 149:
        return _unified_bus_base + col
    else:
        return None  # Out of range


def is_valid_unified_bus_index(bus_index: int) -> bool:
    """Check if bus index is in the valid unified range (base+0 to base+148)."""
    bus_min = _unified_bus_base
    bus_max = _unified_bus_base + 148
    return isinstance(bus_index, int) and bus_min <= bus_index <= bus_max


def is_finite(value: float) -> bool:
    """Check if value is finite (not NaN or infinity)."""
    return math.isfinite(value)


def aggregate_contributions(
    contributions: List[Tuple[int, int, float]]
) -> Dict[int, float]:
    """
    Aggregate boid contributions by bus index.

    Args:
        contributions: List of (row, col, offset) tuples from boid cells

    Returns:
        Dictionary mapping bus_index -> summed offset

    Per spec:
    - Maps each (row, col) via grid_to_bus
    - Sums contributions for the same bus index
    - Filters out non-finite offsets
    - All columns (including generators) now map to unified buses
    """
    aggregated: Dict[int, float] = {}

    for row, col, offset in contributions:
        # Skip non-finite offsets per wire contract
        if not is_finite(offset):
            continue

        bus_index = grid_to_bus(row, col)
        if bus_index is None:
            continue  # Out of range

        if bus_index in aggregated:
            aggregated[bus_index] += offset
        else:
            aggregated[bus_index] = offset

    # Final pass: filter any sums that became non-finite
    return {k: v for k, v in aggregated.items() if is_finite(v)}


def downselect_snapshot(snapshot: Dict[int, float]) -> Dict[int, float]:
    """
    Apply deterministic downselection if snapshot exceeds 100 entries.

    Args:
        snapshot: Dictionary mapping bus_index -> offset

    Returns:
        Dictionary with at most 100 entries, selected by:
        1. Primary: abs(offset) descending
        2. Tie-breaker: bus_index ascending

    Per spec v4: keeps the 100 most significant offsets.
    """
    if len(snapshot) <= MAX_OFFSET_PAIRS:
        return snapshot

    # Sort by abs(offset) descending, then bus_index ascending
    sorted_items = sorted(
        snapshot.items(),
        key=lambda item: (-abs(item[1]), item[0])
    )

    # Keep first 100
    return dict(sorted_items[:MAX_OFFSET_PAIRS])


def prepare_offsets_message(snapshot: Dict[int, float]) -> List:
    """
    Prepare flat list of args for /noise/boid/offsets OSC message.

    Args:
        snapshot: Dictionary mapping bus_index -> offset

    Returns:
        Flat list: [busIndex1, offset1, busIndex2, offset2, ...]

    Per spec: deterministic ordering by bus index ascending.
    """
    args = []
    for bus_index in sorted(snapshot.keys()):
        args.append(bus_index)
        args.append(snapshot[bus_index])
    return args


class BoidBusSender:
    """
    Handles sending boid offsets to SuperCollider via OSC.

    Enforces:
    - Single snapshot per tick
    - Proper enable/disable sequencing
    - Non-finite filtering at wire boundary
    - Downselection if > 100 entries
    """

    def __init__(self, osc_client):
        """
        Initialize sender with OSC client.

        Args:
            osc_client: Object with send_message(address, *args) method
        """
        self.osc_client = osc_client
        self._enabled = False
        self._last_snapshot: Dict[int, float] = {}

    def enable(self):
        """
        Enable boid modulation.

        Per spec: Send enable before or in same tick as first offsets.
        """
        if not self._enabled:
            from src.utils.logger import logger
            logger.info("Boid modulation ENABLED", component="BOID")
            self.osc_client.send_message('/noise/boid/enable', 1)
            self._enabled = True

    def disable(self):
        """
        Disable boid modulation.

        Per spec: Also sends clear for faster convergence.
        """
        if self._enabled:
            from src.utils.logger import logger
            logger.info("Boid modulation DISABLED", component="BOID")
            self.osc_client.send_message('/noise/boid/enable', 0)
            self.osc_client.send_message('/noise/boid/clear', 1)
            self._enabled = False
            self._last_snapshot = {}

    def send_offsets(self, contributions: List[Tuple[int, int, float]]):
        """
        Aggregate and send boid offsets for current tick.

        Args:
            contributions: List of (row, col, offset) tuples

        Per spec:
        - Aggregates by bus index
        - Filters non-finite values
        - Downselects if > 100 entries
        - Sends single snapshot message
        """
        if not self._enabled:
            return

        # Aggregate contributions
        snapshot = aggregate_contributions(contributions)

        # Apply downselection if needed
        snapshot = downselect_snapshot(snapshot)

        # Store for debugging/inspection
        self._last_snapshot = snapshot

        if not snapshot:
            # Empty snapshot - send clear
            self.osc_client.send_message('/noise/boid/clear', 1)
        else:
            # Send offsets as flat list [busIndex1, offset1, busIndex2, offset2, ...]
            args = prepare_offsets_message(snapshot)
            self.osc_client.send_message('/noise/boid/offsets', args)

    def clear(self):
        """Clear all boid offsets without disabling."""
        self.osc_client.send_message('/noise/boid/clear', 1)
        self._last_snapshot = {}

    @property
    def is_enabled(self) -> bool:
        """Return current enabled state."""
        return self._enabled

    @property
    def last_snapshot(self) -> Dict[int, float]:
        """Return last sent snapshot (for debugging)."""
        return self._last_snapshot.copy()


# Bus index to target key mapping (for debugging/logging)
def bus_index_to_target_key(bus_index: int) -> Optional[str]:
    """
    Convert bus index to human-readable target key.

    Useful for debugging and logging.
    """
    if not is_valid_unified_bus_index(bus_index):
        return None

    # Bus layout relative to bus base (149 total):
    # - base+0 to base+39: gen core params (8 slots x 5 params)
    # - base+40 to base+79: gen custom params (8 slots x 5 custom)
    # - base+80 to base+107: mod slot params (4 slots x 7 params)
    # - base+108 to base+131: channel params (8 channels x 3 params)
    # - base+132 to base+148: FX params

    offset = bus_index - _unified_bus_base

    # Gen core params (indices 0-39)
    if 0 <= offset < 40:
        slot = (offset // 5) + 1
        param_idx = offset % 5
        param_names = ['freq', 'cutoff', 'res', 'attack', 'decay']
        return f"gen_{slot}_{param_names[param_idx]}"

    # Gen custom params (indices 40-79)
    elif 40 <= offset < 80:
        local = offset - 40
        slot = (local // 5) + 1
        custom_idx = local % 5
        return f"gen_{slot}_custom{custom_idx}"

    # Mod slot params (indices 80-107)
    elif 80 <= offset < 108:
        local = offset - 80
        slot = (local // 7) + 1
        param = local % 7
        return f"mod_{slot}_p{param}"

    # Channel params (indices 108-131)
    elif 108 <= offset < 132:
        local = offset - 108
        channel = (local // 3) + 1
        param_idx = local % 3
        param_names = ['echo', 'verb', 'pan']
        return f"chan_{channel}_{param_names[param_idx]}"

    # FX params (indices 132-148)
    elif 132 <= offset < 149:
        fx_keys = [
            'fx_heat_drive',  # 132
            'fx_echo_time', 'fx_echo_feedback', 'fx_echo_tone',  # 133-135
            'fx_echo_wow', 'fx_echo_spring', 'fx_echo_verbSend',  # 136-138
            'fx_reverb_size', 'fx_reverb_decay', 'fx_reverb_tone',  # 139-141
            'fx_dualFilter_drive', 'fx_dualFilter_freq1', 'fx_dualFilter_freq2',  # 142-144
            'fx_dualFilter_reso1', 'fx_dualFilter_reso2', 'fx_dualFilter_syncAmt',  # 145-147
            'fx_dualFilter_harmonics'  # 148
        ]
        idx = offset - 132
        if idx < len(fx_keys):
            return fx_keys[idx]

    return None


# Aliases for backward compatibility with older test files
# Some tests use different function names - these aliases ensure compatibility
grid_to_offset_index = grid_to_bus
offset_index_to_target_key = bus_index_to_target_key
