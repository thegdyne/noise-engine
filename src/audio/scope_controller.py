"""
Scope Controller
Manages oscilloscope commands to SuperCollider.

Handles slot selection, threshold, freeze, and enable/disable.
Waveform data flows separately: SC → OSC bridge → main_frame → scope_widget.
"""

from PyQt5.QtCore import QObject

from src.utils.logger import logger


class ScopeController(QObject):
    """Manages scope tap communication with SuperCollider."""

    def __init__(self, osc_bridge):
        super().__init__()
        self.osc = osc_bridge

        # State
        self.is_frozen = False
        self.tapped_slot = 0  # 0-indexed
        self.threshold = 0.0
        self.enabled = False

    def enable(self):
        """Start scope streaming from SC."""
        self.enabled = True
        self.osc.send('scope_enable', [1])

    def disable(self):
        """Stop scope streaming."""
        self.enabled = False
        self.osc.send('scope_enable', [0])

    def set_slot(self, slot: int):
        """Switch scope to tap a different generator slot (0-7)."""
        if not 0 <= slot < 8:
            return
        self.tapped_slot = slot
        self.osc.send('scope_slot', [slot])

    def set_threshold(self, threshold: float):
        """Set trigger threshold (-1.0 to 1.0)."""
        self.threshold = max(-1.0, min(1.0, threshold))
        self.osc.send('scope_threshold', [self.threshold])

    def freeze(self, frozen: bool):
        """Freeze/unfreeze display."""
        self.is_frozen = frozen
        self.osc.send('scope_freeze', [1 if frozen else 0])
