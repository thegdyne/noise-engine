"""
Boid Bus Integration - Grid to Bus Mapping and OSC Protocol

Implements the boid bus integration spec v4:
- Grid to bus mapping for unified buses (columns 80-150 -> bus indices 1000-1070)
- Aggregation of boid contributions per bus index
- Deterministic downselection (max 100 entries)
- Non-finite value filtering
- Single-snapshot-per-tick OSC sending
"""

from typing import Dict, List, Optional, Tuple
import math


# Grid layout constants per spec
GRID_TOTAL_COLUMNS = 151  # 0..150

# Column ranges
GENERATOR_COLS = (0, 79)      # 80 cols: legacy path
MOD_SLOT_COLS = (80, 107)     # 28 cols -> bus 1000-1027
CHANNEL_COLS = (108, 131)     # 24 cols -> bus 1028-1051
FX_COLS = (132, 150)          # 19 cols -> bus 1052-1070

# Unified bus index range
UNIFIED_BUS_MIN = 1000
UNIFIED_BUS_MAX = 1070

# Protocol constraints
MAX_OFFSET_PAIRS = 100


def grid_to_bus(row: int, col: int) -> Optional[int]:
    """
    Map grid coordinates to unified bus index.

    Args:
        row: Grid row (not used in this phase, included for future compatibility)
        col: Grid column (0-150)

    Returns:
        Bus index (1000-1070) for unified buses, or None for generator columns (0-79)

    Per spec v4:
    - col 0-79: None (generator path, handled separately)
    - col 80-107: bus 1000-1027 (mod slot params)
    - col 108-131: bus 1028-1051 (channel params)
    - col 132-150: bus 1052-1070 (FX params)
    """
    if col < 80:
        return None  # Generator path
    elif 80 <= col < 108:
        return 1000 + (col - 80)
    elif 108 <= col < 132:
        return 1028 + (col - 108)
    elif 132 <= col < 151:
        return 1052 + (col - 132)
    else:
        return None  # Out of range


def is_valid_unified_bus_index(bus_index: int) -> bool:
    """Check if bus index is in the valid unified range (1000-1070)."""
    return isinstance(bus_index, int) and UNIFIED_BUS_MIN <= bus_index <= UNIFIED_BUS_MAX


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
    - Ignores generator columns (col < 80)
    """
    aggregated: Dict[int, float] = {}

    for row, col, offset in contributions:
        # Skip non-finite offsets per wire contract
        if not is_finite(offset):
            continue

        bus_index = grid_to_bus(row, col)
        if bus_index is None:
            continue  # Generator column or out of range

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
            self.osc_client.send_message('/noise/boid/enable', 1)
            self._enabled = True

    def disable(self):
        """
        Disable boid modulation.

        Per spec: Also sends clear for faster convergence.
        """
        if self._enabled:
            self.osc_client.send_message('/noise/boid/enable', 0)
            self.osc_client.send_message('/noise/boid/clear')
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
            self.osc_client.send_message('/noise/boid/clear')
        else:
            # Send offsets
            args = prepare_offsets_message(snapshot)
            self.osc_client.send_message('/noise/boid/offsets', *args)

    def clear(self):
        """Clear all boid offsets without disabling."""
        self.osc_client.send_message('/noise/boid/clear')
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

    # Mod slot params: 1000-1027 (4 slots x 7 params)
    if 1000 <= bus_index <= 1027:
        offset = bus_index - 1000
        slot = (offset // 7) + 1
        param = offset % 7
        return f"mod_{slot}_p{param}"

    # Channel params: 1028-1051 (8 channels x 3 params)
    elif 1028 <= bus_index <= 1051:
        offset = bus_index - 1028
        channel = (offset // 3) + 1
        param_idx = offset % 3
        param_names = ['echo', 'verb', 'pan']
        return f"chan_{channel}_{param_names[param_idx]}"

    # FX params: 1052-1070
    elif 1052 <= bus_index <= 1070:
        fx_keys = [
            'fx_heat_drive', 'fx_heat_mix',  # 1052-1053
            'fx_echo_time', 'fx_echo_feedback', 'fx_echo_tone',  # 1054-1056
            'fx_echo_wow', 'fx_echo_spring', 'fx_echo_verbSend',  # 1057-1059
            'fx_verb_size', 'fx_verb_decay', 'fx_verb_tone',  # 1060-1062
            'fx_fb_drive', 'fx_fb_freq1', 'fx_fb_freq2',  # 1063-1065
            'fx_fb_reso1', 'fx_fb_reso2', 'fx_fb_syncAmt',  # 1066-1068
            'fx_fb_harmonics', 'fx_fb_mix'  # 1069-1070
        ]
        idx = bus_index - 1052
        if idx < len(fx_keys):
            return fx_keys[idx]

    return None
