"""
Boid Bus Integration - Grid to Bus Mapping and OSC Protocol

Implements the boid bus integration per GROUND spec:
- Grid to bus mapping: columns 0-175 map directly to target indices 0-175
- Aggregation of boid contributions per target index
- Deterministic downselection (max 100 entries)
- Non-finite value filtering
- Single-snapshot-per-tick OSC sending

Target Layout v3 (176 total - UI Refresh expansion):
| Index     | Count | Category       | Parameters                                       |
|-----------|-------|----------------|--------------------------------------------------|
| 0-39      | 40    | Gen Core       | 8 slots x 5 params (freq, cutoff, res, atk, dec) |
| 40-79     | 40    | Gen Custom     | 8 slots x 5 custom params (custom0-4)            |
| 80-107    | 28    | Mod Slots      | 4 slots x 7 params (P0-P6)                       |
| 108-147   | 40    | Channels       | 8 slots x 5 params (fx1, fx2, fx3, fx4, pan)     |
| 148-167   | 20    | FX Slots       | 4 slots x 5 params (p1, p2, p3, p4, return)      |
| 168-175   | 8     | Master Inserts | DualFilter 7 params + Heat 1 param               |

OSC Protocol:
- Python sends target indices 0-175 directly (NOT absolute bus indices)
- SC handles the mapping to actual bus indices internally
"""

from typing import Dict, List, Optional, Tuple
import math

from src.config import OSC_PATHS, MOD_MATRIX_COLS
from src.utils.boid_scales import get_boid_scales


# Grid layout constants per spec v3 (SSOT: matches unified bus target key count)
GRID_TOTAL_COLUMNS = MOD_MATRIX_COLS  # 0..175

# Column/target ranges (column == target index)
# v3 layout - UI Refresh expansion
GEN_CORE_COLS = (0, 39)       # 40 cols -> 8 slots x 5 core params (unchanged)
GEN_CUSTOM_COLS = (40, 79)    # 40 cols -> 8 slots x 5 custom params (unchanged)
MOD_SLOT_COLS = (80, 107)     # 28 cols -> 4 slots x 7 params (unchanged)
CHANNEL_COLS = (108, 147)     # 40 cols -> 8 channels x 5 params (fx1-4 + pan)
FX_SLOT_COLS = (148, 167)     # 20 cols -> 4 FX slots x 5 params (p1-4 + return)
MASTER_INSERT_COLS = (168, 175)  # 8 cols -> DualFilter 7 + Heat 1

# Protocol constraints
MAX_OFFSET_PAIRS = 100


def grid_to_bus(row: int, col: int) -> int:
    """
    Map grid coordinates to unified target index.

    Args:
        row: Grid row (0-15, validated but not used in mapping)
        col: Grid column (0-175)

    Returns:
        Target index (same as col, 0-175)

    Raises:
        ValueError: If row or col is out of valid range

    Per GROUND spec: target_index = col (row is for simulation/visualization only).
    """
    if not (0 <= row <= 15):
        raise ValueError(f"row {row} out of range [0, 15]")
    if not (0 <= col <= 175):
        raise ValueError(f"col {col} out of range [0, 175]")
    return col


def is_valid_target_index(target_index: int) -> bool:
    """Check if target index is in the valid range (0-175)."""
    return isinstance(target_index, int) and 0 <= target_index <= 175


def is_finite(value: float) -> bool:
    """Check if value is finite (not NaN or infinity)."""
    return math.isfinite(value)


def aggregate_contributions(
    contributions: List[Tuple[int, int, float]]
) -> Dict[int, float]:
    """
    Aggregate boid contributions by target index.

    Args:
        contributions: List of (row, col, offset) tuples from boid cells

    Returns:
        Dictionary mapping target_index (0-148) -> summed offset

    Per spec:
    - Validates and maps each (row, col) via grid_to_bus
    - Sums contributions for the same target index (row ignored in aggregation)
    - Filters out non-finite offsets
    - Drops invalid contributions silently (does not raise)
    """
    aggregated: Dict[int, float] = {}

    for row, col, offset in contributions:
        # Skip non-finite offsets per wire contract
        if not is_finite(offset):
            continue

        # Map to target index, drop invalid contributions
        try:
            target_index = grid_to_bus(row, col)
        except ValueError:
            continue  # Drop invalid contributions silently

        # Defensive range check (should not happen if grid_to_bus is correct)
        if not (0 <= target_index <= 175):
            continue

        if target_index in aggregated:
            aggregated[target_index] += offset
        else:
            aggregated[target_index] = offset

    # Final pass: filter any sums that became non-finite
    return {k: v for k, v in aggregated.items() if is_finite(v)}


def downselect_snapshot(snapshot: Dict[int, float]) -> Dict[int, float]:
    """
    Apply deterministic downselection if snapshot exceeds 100 entries.

    Args:
        snapshot: Dictionary mapping target_index -> offset

    Returns:
        Dictionary with at most 100 entries, selected by:
        1. Primary: abs(offset) descending
        2. Tie-breaker: target_index ascending

    Per spec: keeps the 100 most significant offsets.
    """
    if len(snapshot) <= MAX_OFFSET_PAIRS:
        return snapshot

    # Sort by abs(offset) descending, then target_index ascending
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
        snapshot: Dictionary mapping target_index (0-148) -> offset

    Returns:
        Flat list: [targetIndex1, offset1, targetIndex2, offset2, ...]
        Target indices are sent directly (0-148), SC handles bus mapping.

    Per spec: deterministic ordering by target index ascending.
    """
    args = []
    for target_index in sorted(snapshot.keys()):
        args.append(int(target_index))  # Ensure int for OSC int32
        args.append(float(snapshot[target_index]))  # Ensure float for OSC float32
    return args


class BoidBusSender:
    """
    Handles sending boid offsets to SuperCollider via OSC.

    Enforces:
    - Single snapshot per tick
    - Proper enable/disable sequencing
    - Non-finite filtering at wire boundary
    - Downselection if > 100 entries
    - Sends target indices 0-148 (not absolute bus indices)
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
            self.osc_client.send_message(OSC_PATHS['boid_enable'], 1)
            self._enabled = True

    def disable(self):
        """
        Disable boid modulation.

        Per spec: Also sends clear for faster convergence.
        """
        if self._enabled:
            from src.utils.logger import logger
            logger.info("Boid modulation DISABLED", component="BOID")
            self.osc_client.send_message(OSC_PATHS['boid_enable'], 0)
            self.osc_client.send_message(OSC_PATHS['boid_clear'], 1)
            self._enabled = False
            self._last_snapshot = {}

    def send_offsets(self, contributions: List[Tuple[int, int, float]]):
        """
        Aggregate and send boid offsets for current tick.

        Args:
            contributions: List of (row, col, offset) tuples

        Per GROUND spec:
        - Validates contributions (drops invalid silently)
        - Aggregates by target index (row ignored)
        - Filters non-finite values
        - Downselects if > 100 entries
        - Sends single OSC message with explicit int32/float32 types
        - Sends target indices 0-148 directly (NOT absolute bus indices)
        - Empty payload is a no-op (no message sent)
        - OSC send exceptions propagate to caller
        """
        if not self._enabled:
            return

        # Aggregate contributions (handles validation, drops invalid silently)
        snapshot = aggregate_contributions(contributions)

        # Drop zero offsets per spec
        snapshot = {k: v for k, v in snapshot.items() if v != 0.0}

        # Apply per-target scaling from config
        snapshot = get_boid_scales().scale_snapshot(snapshot)

        # Drop zeros again (scaling may have zeroed some)
        snapshot = {k: v for k, v in snapshot.items() if v != 0.0}

        # Apply downselection if needed
        snapshot = downselect_snapshot(snapshot)

        # Store for debugging/inspection
        self._last_snapshot = snapshot

        if not snapshot:
            # Empty payload - no-op per spec (don't send anything)
            return

        # Build OSC message with explicit types per GROUND spec
        # Uses OscMessageBuilder to ensure int32 for indices, float32 for offsets
        from pythonosc.osc_message_builder import OscMessageBuilder

        builder = OscMessageBuilder(address=OSC_PATHS['boid_offsets'])
        for target_index in sorted(snapshot.keys()):
            # Send target index directly (0-148), SC handles bus mapping
            builder.add_arg(int(target_index), arg_type='i')  # int32
            builder.add_arg(float(snapshot[target_index]), arg_type='f')  # float32

        msg = builder.build()
        self.osc_client.send(msg)

    def clear(self):
        """Clear all boid offsets without disabling."""
        self.osc_client.send_message(OSC_PATHS['boid_clear'], 1)
        self._last_snapshot = {}

    @property
    def is_enabled(self) -> bool:
        """Return current enabled state."""
        return self._enabled

    @property
    def last_snapshot(self) -> Dict[int, float]:
        """Return last sent snapshot (for debugging)."""
        return self._last_snapshot.copy()


def target_index_to_key(target_index: int) -> Optional[str]:
    """
    Convert target index to human-readable target key.

    Args:
        target_index: Target index (0-175)

    Returns:
        Human-readable key like 'gen_1_freq', 'mod_2_p3', 'chan_1_fx1', etc.
        Returns None if index is out of range.

    Useful for debugging and logging.

    v3 layout (176 targets):
    - 0-39: Gen core (unchanged)
    - 40-79: Gen custom (unchanged)
    - 80-107: Mod slots (unchanged)
    - 108-147: Channels (expanded to 5 params: fx1, fx2, fx3, fx4, pan)
    - 148-167: FX slots (new: 4 slots x 5 params)
    - 168-175: Master inserts (DualFilter 7 + Heat 1)
    """
    if not is_valid_target_index(target_index):
        return None

    # Gen core params (indices 0-39) - UNCHANGED
    if 0 <= target_index < 40:
        slot = (target_index // 5) + 1
        param_idx = target_index % 5
        param_names = ['freq', 'cutoff', 'res', 'attack', 'decay']
        return f"gen_{slot}_{param_names[param_idx]}"

    # Gen custom params (indices 40-79) - UNCHANGED
    elif 40 <= target_index < 80:
        local = target_index - 40
        slot = (local // 5) + 1
        custom_idx = local % 5
        return f"gen_{slot}_custom{custom_idx}"

    # Mod slot params (indices 80-107) - UNCHANGED
    elif 80 <= target_index < 108:
        local = target_index - 80
        slot = (local // 7) + 1
        param = local % 7
        return f"mod_{slot}_p{param}"

    # Channel params (indices 108-147) - v3 EXPANDED to 5 params
    elif 108 <= target_index < 148:
        local = target_index - 108
        channel = (local // 5) + 1
        param_idx = local % 5
        param_names = ['fx1', 'fx2', 'fx3', 'fx4', 'pan']
        return f"chan_{channel}_{param_names[param_idx]}"

    # FX slot params (indices 148-167) - v3 NEW
    elif 148 <= target_index < 168:
        local = target_index - 148
        slot = (local // 5) + 1
        param_idx = local % 5
        param_names = ['p1', 'p2', 'p3', 'p4', 'return']
        return f"fx_slot{slot}_{param_names[param_idx]}"

    # Master insert params (indices 168-175) - v3 REORGANIZED
    elif 168 <= target_index < 176:
        master_keys = [
            'fx_fb_drive',      # 168
            'fx_fb_freq1',      # 169
            'fx_fb_reso1',      # 170
            'fx_fb_freq2',      # 171
            'fx_fb_reso2',      # 172
            'fx_fb_syncAmt',    # 173
            'fx_fb_harmonics',  # 174
            'fx_heat_drive',    # 175
        ]
        idx = target_index - 168
        if idx < len(master_keys):
            return master_keys[idx]

    return None


# Aliases for backward compatibility
grid_to_offset_index = grid_to_bus
bus_index_to_target_key = target_index_to_key  # Now works on target index directly
offset_index_to_target_key = target_index_to_key
