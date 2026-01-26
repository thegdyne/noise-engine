"""
BoidPulseManager - Visual feedback for boid-targeted controls.

Pulses/glows controls currently targeted by boids, creating a visual link
between the boid panel visualiser and the affected parameters.

SSOT Compliance:
  Widget lookup uses findChild with unified target keys.
  Widgets must have objectName set to their unified key (e.g., 'fx_slot1_p1').
"""

from __future__ import annotations

import time
from typing import Dict, Tuple, Set, Optional, TYPE_CHECKING

from PyQt5.QtWidgets import QWidget

from src.config import (
    UNIFIED_BUS_TARGET_KEYS,
    parse_target_key,
)
from src.utils.boid_scales import get_boid_scales

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

    Widget lookup is SSOT-compliant: uses findChild with unified target keys.
    """

    def __init__(self, main_frame: 'MainFrame'):
        self._main = main_frame
        self._prev_cols: Set[int] = set()
        self._pulse_timestamps: Dict[int, float] = {}
        self._pulse_base: Dict[int, float] = {}  # Depth-scaled intensity at entry
        self._last_intensity: Dict[int, float] = {}
        # Cache widget lookups (cleared on build_registry)
        self._widget_cache: Dict[int, Optional[QWidget]] = {}

    def build_registry(self) -> None:
        """
        Build widget cache. Call after UI fully constructed.

        Uses SSOT-compliant findChild lookup with unified target keys.
        Widgets must have objectName matching their unified key.
        """
        self._widget_cache.clear()
        for col, target_key in enumerate(UNIFIED_BUS_TARGET_KEYS):
            # Direct findChild lookup - widgets must have objectName set
            widget = self._main.findChild(QWidget, target_key)
            self._widget_cache[col] = widget

    def _get_widget(self, col: int) -> Optional[QWidget]:
        """
        Get widget for column index.

        Uses cached findChild result. Falls back to live lookup if not cached.
        """
        if col in self._widget_cache:
            return self._widget_cache[col]

        # Fallback: live lookup (should not normally be needed)
        if col < len(UNIFIED_BUS_TARGET_KEYS):
            target_key = UNIFIED_BUS_TARGET_KEYS[col]
            widget = self._main.findChild(QWidget, target_key)
            self._widget_cache[col] = widget
            return widget
        return None

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

        # Detect entries → start pulse (scaled by depth)
        entered = current_cols - self._prev_cols
        for col in entered:
            self._pulse_timestamps[col] = now
            # Store depth-scaled intensity as pulse base
            self._pulse_base[col] = col_intensity.get(col, 1.0)

        # Clean up exited pulse timestamps
        exited = self._prev_cols - current_cols
        for col in exited:
            self._pulse_timestamps.pop(col, None)
            self._pulse_base.pop(col, None)

        # Compute final intensities
        final_intensity: Dict[int, float] = {}

        for col in current_cols | set(self._pulse_timestamps.keys()):
            glow = col_intensity.get(col, 0.0)

            # Compute pulse decay (scaled by depth at entry)
            pulse = 0.0
            if col in self._pulse_timestamps:
                elapsed = now - self._pulse_timestamps[col]
                base = self._pulse_base.get(col, 1.0)
                pulse = max(0.0, base * (1.0 - elapsed / PULSE_DURATION))
                if pulse <= 0:
                    del self._pulse_timestamps[col]
                    self._pulse_base.pop(col, None)

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
        """Apply glow to widget for column using SSOT findChild lookup."""
        widget = self._get_widget(col)
        if widget and hasattr(widget, 'set_boid_glow'):
            # Scale intensity by per-target scale from config
            scale = get_boid_scales().get_scale(col)
            scaled_intensity = intensity * scale
            muted = self._is_target_muted(col)
            widget.set_boid_glow(scaled_intensity, muted)

    def _is_target_muted(self, col: int) -> bool:
        """Check if target at column is muted/empty/bypassed."""
        if col >= len(UNIFIED_BUS_TARGET_KEYS):
            return False

        target_key = UNIFIED_BUS_TARGET_KEYS[col]
        info = parse_target_key(target_key)
        if not info:
            return False

        zone = info['zone']
        slot = info.get('slot')

        if zone in ('gen_core', 'gen_custom'):
            # Generator: empty or muted
            grid = getattr(self._main, 'generator_grid', None)
            if grid:
                slot_widget = grid.get_slot(slot)
                if slot_widget:
                    if getattr(slot_widget, 'generator_type', None) == 'Empty':
                        return True
                    if getattr(slot_widget, 'muted', False):
                        return True
        elif zone == 'mod':
            # Modulator: empty
            grid = getattr(self._main, 'modulator_grid', None)
            if grid:
                slot_widget = grid.get_slot(slot)
                if slot_widget:
                    if getattr(slot_widget, 'generator_name', None) == 'Empty':
                        return True
        elif zone == 'chan':
            # Channel: muted
            mixer = getattr(self._main, 'mixer_panel', None)
            if mixer:
                channel = mixer.get_channel(slot)
                if channel and getattr(channel, 'muted', False):
                    return True
        elif zone == 'fx_slot':
            # FX slot: empty or bypassed
            fx_grid = getattr(self._main, 'fx_grid', None)
            if fx_grid:
                slot_widget = fx_grid.get_slot(slot)
                if slot_widget:
                    if getattr(slot_widget, 'fx_type', None) == 'Empty':
                        return True
                    if getattr(slot_widget, 'bypassed', False):
                        return True
        elif zone in ('fx_master', 'fx'):
            # Master FX: bypassed (Heat/Filter now in master_section via MasterChain)
            master_section = getattr(self._main, 'master_section', None)
            if master_section:
                param = info['param']
                # Check which module and if bypassed
                if param.startswith('heat_'):
                    heat = getattr(master_section, 'heat', None)
                    if heat and getattr(heat, 'bypassed', False):
                        return True
                elif param.startswith('fb_'):
                    filt = getattr(master_section, 'filter', None)
                    if filt and getattr(filt, 'bypassed', False):
                        return True

        return False
