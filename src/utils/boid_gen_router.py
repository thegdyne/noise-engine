"""
Boid Generator Router - Routes boid contributions to generator parameters

Maps GEN zone columns (0-79) to generator parameters:
- 8 generators × 10 parameters each = 80 columns
- Per generator: freq, cutoff, res, attack, decay, custom0-4

Uses OSC to send offset values to SuperCollider.
"""

from typing import Dict, List, Tuple, Optional
from src.config import OSC_PATHS


# Grid layout for GEN zone
COLS_PER_GEN = 10
NUM_GENERATORS = 8

# Parameter mapping within each generator's 10 columns
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


def col_to_gen_param(col: int) -> Optional[Tuple[int, str]]:
    """
    Map a column (0-79) to generator slot and parameter name.

    Returns:
        Tuple of (slot_id 1-8, param_name) or None if out of range
    """
    if col < 0 or col >= 80:
        return None

    gen_index = col // COLS_PER_GEN  # 0-7
    param_index = col % COLS_PER_GEN  # 0-9

    slot_id = gen_index + 1  # 1-8
    param_name = GEN_PARAM_MAP.get(param_index)

    if param_name is None:
        return None

    return (slot_id, param_name)


class BoidGenRouter:
    """
    Routes boid contributions from GEN zone to generator parameters via OSC.
    """

    def __init__(self, osc_client):
        """
        Initialize with OSC client for sending messages.

        Args:
            osc_client: python-osc SimpleUDPClient
        """
        self.osc_client = osc_client
        self._last_offsets: Dict[Tuple[int, str], float] = {}

    def route_contributions(self, contributions: List[Tuple[int, int, float]]) -> None:
        """
        Route boid contributions to generator parameters.

        Args:
            contributions: List of (row, col, value) tuples for GEN zone (col 0-79)
        """
        if not self.osc_client:
            return

        # Aggregate contributions by (slot_id, param_name)
        offsets: Dict[Tuple[int, str], float] = {}

        for row, col, value in contributions:
            result = col_to_gen_param(col)
            if result is None:
                continue

            slot_id, param_name = result
            key = (slot_id, param_name)

            if key in offsets:
                offsets[key] += value
            else:
                offsets[key] = value

        # Send OSC messages for each offset
        for (slot_id, param_name), offset in offsets.items():
            self._send_param_offset(slot_id, param_name, offset)

        # Clear params that no longer have contributions
        for key in list(self._last_offsets.keys()):
            if key not in offsets:
                slot_id, param_name = key
                self._send_param_offset(slot_id, param_name, 0.0)

        self._last_offsets = offsets

    def _send_param_offset(self, slot_id: int, param_name: str, offset: float) -> None:
        """Send offset for a single generator parameter."""
        # Map param_name to OSC path
        if param_name.startswith('custom'):
            # Custom params: /noise/gen/custom/{slot}/{index}
            param_index = int(param_name[6])  # 'custom0' -> 0
            path = f"{OSC_PATHS['gen_custom']}/{slot_id}/{param_index}"
            # Custom params use relative offset
            self.osc_client.send_message(f"{path}/boid_offset", [offset])
        else:
            # Standard params
            path_key = f'gen_{param_name}'
            if path_key in OSC_PATHS:
                base_path = OSC_PATHS[path_key]
                # Send boid offset as separate message
                self.osc_client.send_message(f"{base_path}/boid_offset", [slot_id, offset])

    def clear(self) -> None:
        """Clear all generator offsets."""
        if self.osc_client:
            # Send bulk clear for efficiency
            self.osc_client.send_message('/noise/gen/boid/clear', [])
        self._last_offsets = {}
