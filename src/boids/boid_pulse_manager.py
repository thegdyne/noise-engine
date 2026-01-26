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
    """

    def __init__(self, main_frame: 'MainFrame'):
        self._main = main_frame
        self._prev_cols: Set[int] = set()
        self._pulse_timestamps: Dict[int, float] = {}
        self._pulse_base: Dict[int, float] = {}  # Depth-scaled intensity at entry
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
            # mod params are 'p0', 'p1', etc. - extract index
            try:
                param_idx = int(param.replace('p', ''))
            except ValueError:
                return None
            return lambda s=slot, idx=param_idx: self._resolve_mod_widget(s, idx)
        elif zone == 'chan':
            return lambda s=slot, p=param: self._resolve_chan_widget(s, p)
        elif zone == 'fx_slot':
            return lambda s=slot, p=param: self._resolve_fx_slot_widget(s, p)
        elif zone == 'fx_master':
            return lambda p=param: self._resolve_fx_master_widget(p)
        elif zone == 'fx':
            # Legacy zone - try master widgets first
            return lambda p=param: self._resolve_fx_master_widget(p)
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

    def _resolve_mod_widget(self, slot: int, param_index: int) -> Optional[QWidget]:
        """Resolve modulator slot param widget."""
        grid = getattr(self._main, 'modulator_grid', None)
        if not grid:
            return None
        slot_widget = grid.get_slot(slot)
        if not slot_widget:
            return None
        return slot_widget.get_param_widget(param_index)

    def _resolve_chan_widget(self, slot: int, param: str) -> Optional[QWidget]:
        """Resolve mixer channel param widget."""
        mixer = getattr(self._main, 'mixer_panel', None)
        if not mixer:
            return None
        channel = mixer.get_channel(slot)
        if not channel:
            return None
        return channel.get_param_widget(param)

    def _resolve_fx_slot_widget(self, slot: int, param: str) -> Optional[QWidget]:
        """Resolve FX slot param widget (p1-p4, return)."""
        fx_grid = getattr(self._main, 'fx_grid', None)
        if not fx_grid:
            return None
        slot_widget = fx_grid.get_slot(slot)
        if not slot_widget:
            return None
        # Map param names to slider keys
        if param in ('p1', 'p2', 'p3', 'p4', 'return'):
            return slot_widget.sliders.get(param)
        return None

    def _resolve_fx_master_widget(self, param: str) -> Optional[QWidget]:
        """Resolve master FX param widget (heat, dual filter)."""
        inline_fx = getattr(self._main, 'inline_fx', None)
        if not inline_fx:
            return None
        return inline_fx.get_param_widget(param)

    def _resolve_fx_widget(self, param: str) -> Optional[QWidget]:
        """Resolve FX param widget (legacy)."""
        return self._resolve_fx_master_widget(param)

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
        """Apply glow to widget for column."""
        resolver = self._target_resolvers.get(col)
        if not resolver:
            return
        widget = resolver()
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
            # Master FX: bypassed
            inline_fx = getattr(self._main, 'inline_fx', None)
            if inline_fx:
                param = info['param']
                # Check which module and if bypassed
                if param.startswith('heat_'):
                    if getattr(inline_fx.heat, 'bypassed', False):
                        return True
                elif param.startswith('fb_'):
                    if getattr(inline_fx.filter, 'bypassed', False):
                        return True

        return False
