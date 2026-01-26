"""
BoidPulseManager - Visual feedback for boid-targeted controls.

Pulses/glows controls currently targeted by boids, creating a visual link
between the boid panel visualiser and the affected parameters.
"""

from __future__ import annotations

import time
from typing import Dict, Tuple, Set, Callable, Optional, TYPE_CHECKING

from PyQt5.QtWidgets import QWidget

from src.config import (
    UNIFIED_BUS_TARGET_KEYS,
    parse_target_key,
)

if TYPE_CHECKING:
    from src.gui.main_frame import MainFrame

# Constants
PULSE_DURATION = 0.33      # seconds for full pulse decay
INTENSITY_EPSILON = 0.01   # minimum change to trigger repaint


class BoidPulseManager:
    """
    Manages boid glow visualization on UI widgets.

    Receives cells_updated signal from BoidController, computes intensities,
    and dispatches glow values to target widgets.
    """

    def __init__(self, main_frame: 'MainFrame'):
        self._main = main_frame
        self._prev_cols: Set[int] = set()
        self._pulse_timestamps: Dict[int, float] = {}
        self._last_intensity: Dict[int, float] = {}
        self._target_resolvers: Dict[int, Callable[[], Optional[QWidget]]] = {}

    def build_registry(self) -> None:
        """Build col → widget resolver map. Call after UI fully constructed."""
        for col, target_key in enumerate(UNIFIED_BUS_TARGET_KEYS):
            resolver = self._make_resolver(target_key)
            if resolver:
                self._target_resolvers[col] = resolver

    def _make_resolver(self, target_key: str) -> Optional[Callable[[], Optional[QWidget]]]:
        """Create a resolver callable for a target key."""
        info = parse_target_key(target_key)
        if not info:
            return None

        zone = info['zone']
        slot = info.get('slot')
        param = info['param']

        if zone == 'gen_core':
            return lambda s=slot, p=param: self._resolve_gen_widget(s, p)
        elif zone == 'gen_custom':
            return lambda s=slot, p=param: self._resolve_gen_widget(s, p)
        elif zone == 'mod':
            # Skip mod slots for now - complex param mapping
            return None
        elif zone == 'chan':
            return lambda s=slot, p=param: self._resolve_chan_widget(s, p)
        elif zone == 'fx':
            # Skip FX for now - complex structure
            return None
        return None

    def _resolve_gen_widget(self, slot: int, param: str) -> Optional[QWidget]:
        """Resolve generator slot param widget."""
        grid = getattr(self._main, 'generator_grid', None)
        if not grid:
            return None
        slot_widget = grid.get_slot(slot)
        if not slot_widget:
            return None
        return slot_widget.get_param_widget(param)

    def _resolve_chan_widget(self, slot: int, param: str) -> Optional[QWidget]:
        """Resolve mixer channel param widget."""
        mixer = getattr(self._main, 'mixer_panel', None)
        if not mixer:
            return None
        channel = mixer.get_channel(slot)
        if not channel:
            return None
        return channel.get_param_widget(param)

    def on_cells_updated(self, cells: Dict[Tuple[int, int], float]) -> None:
        """
        Handle cells update from boid controller.

        Args:
            cells: Dict mapping (row, col) to value (0.0-1.0)
        """
        now = time.monotonic()

        # Build col → intensity map (max policy)
        col_intensity: Dict[int, float] = {}
        for (row, col), value in cells.items():
            col_intensity[col] = max(col_intensity.get(col, 0.0), float(value))

        current_cols = set(col_intensity.keys())

        # Detect entries → start pulse
        entered = current_cols - self._prev_cols
        for col in entered:
            self._pulse_timestamps[col] = now

        # Clean up exited pulse timestamps
        exited = self._prev_cols - current_cols
        for col in exited:
            self._pulse_timestamps.pop(col, None)

        # Compute final intensities
        final_intensity: Dict[int, float] = {}

        for col in current_cols | set(self._pulse_timestamps.keys()):
            glow = col_intensity.get(col, 0.0)

            # Compute pulse decay
            pulse = 0.0
            if col in self._pulse_timestamps:
                elapsed = now - self._pulse_timestamps[col]
                pulse = max(0.0, 1.0 - elapsed / PULSE_DURATION)
                if pulse <= 0:
                    del self._pulse_timestamps[col]

            final_intensity[col] = max(glow, pulse)

        # Update widgets (only if changed)
        for col, intensity in final_intensity.items():
            last = self._last_intensity.get(col, 0.0)
            if abs(intensity - last) > INTENSITY_EPSILON:
                self._apply_glow(col, intensity)
                self._last_intensity[col] = intensity

        # Clear widgets that went to zero
        for col in list(self._last_intensity.keys()):
            if col not in final_intensity or final_intensity[col] <= 0:
                if self._last_intensity[col] > 0:
                    self._apply_glow(col, 0.0)
                self._last_intensity.pop(col, None)

        self._prev_cols = current_cols

    def _apply_glow(self, col: int, intensity: float) -> None:
        """Apply glow to widget for column."""
        resolver = self._target_resolvers.get(col)
        if not resolver:
            return
        widget = resolver()
        if widget and hasattr(widget, 'set_boid_glow'):
            widget.set_boid_glow(intensity)
