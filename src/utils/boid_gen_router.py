"""
Boid Generator Router - Routes boid contributions to generator parameters

Maps GEN zone columns (0-79) to generator parameters:
- 8 generators × 10 parameters each = 80 columns
- Per generator: freq, cutoff, res, attack, decay, custom0-4

Uses OSC to send batched offset values to SuperCollider.
"""

from typing import Dict, List, Tuple, Optional


# Grid layout for GEN zone
COLS_PER_GEN = 10
NUM_GENERATORS = 8

# Parameter mapping within each generator's 10 columns
# Index matches column position within generator's 10-column block
GEN_PARAM_MAP = {
    0: 'frequency',   # Pitch offset
    1: 'cutoff',      # Filter cutoff
    2: 'resonance',   # Filter resonance
    3: 'attack',      # Envelope attack
    4: 'decay',       # Envelope decay
    5: 'custom0',     # Custom param 0
    6: 'custom1',     # Custom param 1
    7: 'custom2',     # Custom param 2
    8: 'custom3',     # Custom param 3
    9: 'custom4',     # Custom param 4
}


def col_to_gen_param(col: int) -> Optional[Tuple[int, int]]:
    """
    Map a column (0-79) to generator slot and parameter index.

    Returns:
        Tuple of (slot_id 1-8, param_index 0-9) or None if out of range
    """
    if col < 0 or col >= 80:
        return None

    gen_index = col // COLS_PER_GEN  # 0-7
    param_index = col % COLS_PER_GEN  # 0-9

    slot_id = gen_index + 1  # 1-8
    return (slot_id, param_index)


class BoidGenRouter:
    """
    Routes boid contributions from GEN zone to generator parameters via OSC.

    Uses batched messaging: one OSC message per tick containing all offsets.
    Format: /noise/gen/boid/offsets [slot1, paramIdx1, val1, slot2, paramIdx2, val2, ...]
    """

    def __init__(self, osc_client):
        """
        Initialize with OSC client for sending messages.

        Args:
            osc_client: python-osc SimpleUDPClient
        """
        self.osc_client = osc_client
        self._last_offsets: Dict[Tuple[int, int], float] = {}

    def route_contributions(self, contributions: List[Tuple[int, int, float]]) -> None:
        """
        Route boid contributions to generator parameters.

        Args:
            contributions: List of (row, col, value) tuples for GEN zone (col 0-79)
        """
        if not self.osc_client:
            return

        # Aggregate contributions by (slot_id, param_index)
        offsets: Dict[Tuple[int, int], float] = {}

        for row, col, value in contributions:
            result = col_to_gen_param(col)
            if result is None:
                continue

            slot_id, param_index = result
            key = (slot_id, param_index)

            if key in offsets:
                offsets[key] += value
            else:
                offsets[key] = value

        # Include zeros for params that no longer have contributions
        for key in self._last_offsets:
            if key not in offsets:
                offsets[key] = 0.0

        # Build batched message: [slot1, paramIdx1, val1, slot2, paramIdx2, val2, ...]
        args = []
        for (slot_id, param_index), offset in offsets.items():
            args.extend([slot_id, param_index, offset])

        # Send single batched message
        if args:
            self.osc_client.send_message('/noise/gen/boid/offsets', args)

        # Update last offsets (excluding zeros)
        self._last_offsets = {k: v for k, v in offsets.items() if v != 0.0}

    def clear(self) -> None:
        """Clear all generator offsets."""
        if self.osc_client:
            # Send empty offsets message to clear
            self.osc_client.send_message('/noise/gen/boid/offsets', [])
        self._last_offsets = {}
