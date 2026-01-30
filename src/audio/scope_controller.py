"""
Scope Controller
Manages oscilloscope data from SuperCollider.

Receives waveform data via OSC and provides it to the scope widget.
Handles slot selection, threshold, and freeze state.
"""

import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal

from src.config import OSC_PATHS
from src.utils.logger import logger


class ScopeController(QObject):
    """Manages scope tap communication with SuperCollider."""

    # Emitted when new waveform data arrives (numpy array)
    frame_received = pyqtSignal(object)

    def __init__(self, osc_bridge):
        super().__init__()
        self.osc = osc_bridge
        self.buf_size = 1024

        # State
        self.is_frozen = False
        self.tapped_slot = 0  # 0-indexed
        self.threshold = 0.0
        self.enabled = False
        self.current_frame = np.zeros(self.buf_size, dtype=np.float32)

    def enable(self):
        """Start scope streaming from SC."""
        self.enabled = True
        if self.osc and self.osc.client:
            self.osc.client.send_message('/noise/scope/enable', [1])

    def disable(self):
        """Stop scope streaming."""
        self.enabled = False
        if self.osc and self.osc.client:
            self.osc.client.send_message('/noise/scope/enable', [0])

    def set_slot(self, slot: int):
        """Switch scope to tap a different generator slot (0-7)."""
        if not 0 <= slot < 8:
            return
        self.tapped_slot = slot
        if self.osc and self.osc.client:
            self.osc.client.send_message('/noise/scope/slot', [slot])

    def set_threshold(self, threshold: float):
        """Set trigger threshold (-1.0 to 1.0)."""
        self.threshold = max(-1.0, min(1.0, threshold))
        if self.osc and self.osc.client:
            self.osc.client.send_message('/noise/scope/threshold', [self.threshold])

    def freeze(self, frozen: bool):
        """Freeze/unfreeze display."""
        self.is_frozen = frozen
        if self.osc and self.osc.client:
            self.osc.client.send_message('/noise/scope/freeze', [1 if frozen else 0])

    def on_scope_data(self, address, *args):
        """Handle incoming scope waveform data from SC.

        Called from OSC dispatcher thread - emits signal for thread-safe UI update.
        """
        if not self.enabled:
            return

        try:
            data = np.array(args, dtype=np.float32)
            if len(data) > 0:
                self.current_frame = data
                self.frame_received.emit(data)
        except Exception:
            pass
