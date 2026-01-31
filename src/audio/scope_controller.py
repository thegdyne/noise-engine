"""
Scope Controller
Manages oscilloscope commands to SuperCollider.

Handles slot selection, threshold, freeze, enable/disable, and debug capture.
Waveform data flows separately: SC → OSC bridge → main_frame → scope_widget.
"""

import csv
import os
import time

import numpy as np
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

        # Debug: last frame Python actually displayed
        self._last_display_frame = None
        self._last_write_pos = 0

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

    def store_display_frame(self, write_pos, raw_buf, trimmed_buf):
        """Store the latest frame data for debug capture.

        Called by main_frame._on_scope_data on every frame.
        """
        self._last_write_pos = write_pos
        self._last_display_frame = {
            'write_pos': write_pos,
            'raw_buf': np.copy(raw_buf) if raw_buf is not None else None,
            'trimmed_buf': np.copy(trimmed_buf) if trimmed_buf is not None else None,
        }

    def debug_capture(self):
        """Trigger a debug capture.

        1. Tells SC to capture raw intermediate bus audio + scope buffer to CSV
        2. Dumps the current Python display frame to a separate CSV
        """
        logger.info("[Scope Debug] Triggering capture...")

        # Tell SC to capture (writes scope_debug.csv in ~/Downloads)
        self.osc.send('scope_debug', [1])

        # Dump Python-side display frame
        self._dump_python_frame()

    def _dump_python_frame(self):
        """Dump the last Python display frame to CSV for comparison.

        Writes ~/Downloads/scope_debug_python.csv with columns:
        - sample: sample index
        - raw_osc_buf: the full 1024-sample buffer as received from SC (before trimming)
        - displayed: the trimmed buffer actually sent to the widget
        """
        frame = self._last_display_frame
        if frame is None:
            logger.warning("[Scope Debug] No Python frame captured yet")
            return

        downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        path = os.path.join(downloads, "scope_debug_python.csv")

        raw_buf = frame.get('raw_buf')
        trimmed_buf = frame.get('trimmed_buf')
        write_pos = frame.get('write_pos', 0)

        with open(path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['sample', 'raw_osc_buf', 'displayed', 'write_pos'])

            raw_len = len(raw_buf) if raw_buf is not None else 0
            trimmed_len = len(trimmed_buf) if trimmed_buf is not None else 0
            max_len = max(raw_len, trimmed_len)

            for i in range(max_len):
                raw_val = float(raw_buf[i]) if raw_buf is not None and i < raw_len else ''
                disp_val = float(trimmed_buf[i]) if trimmed_buf is not None and i < trimmed_len else ''
                wp = write_pos if i == 0 else ''
                writer.writerow([i, raw_val, disp_val, wp])

        logger.info(f"[Scope Debug] Python frame saved to {path} "
                     f"(write_pos={write_pos}, raw={raw_len}, displayed={trimmed_len})")
