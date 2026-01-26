"""
KeyboardController - Handles QWERTY keyboard overlay for MIDI input.

Extracted from MainFrame as Phase 7 of the god-file refactor.
Method names intentionally unchanged from MainFrame for wrapper compatibility.

R1.1: Added focused slot tracking and deferred refresh mechanism.
R1.2: Added ARP support with BPM integration.
"""
from __future__ import annotations

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

from src.gui.keyboard_overlay import KeyboardOverlay
from src.utils.logger import logger


class KeyboardController:
    """Handles QWERTY keyboard overlay for MIDI input."""

    def __init__(self, main_frame):
        self.main = main_frame
        self._focused_slot = 1  # Track last-focused slot (1-indexed)

        # Connect to generator_grid slot click events if available
        if hasattr(self.main, 'generator_grid') and self.main.generator_grid is not None:
            self.main.generator_grid.generator_selected.connect(self._on_slot_selected)
            # Also track env_source changes for live updates
            self.main.generator_grid.generator_env_source_changed.connect(self._on_env_source_changed)

        # Connect to BPM changes for ARP clock sync
        if hasattr(self.main, 'bpm_display') and self.main.bpm_display is not None:
            self.main.bpm_display.bpm_changed.connect(self._on_bpm_changed)

    def _on_slot_selected(self, slot_id: int):
        """Track which slot was last selected/clicked (1-indexed)."""
        if 1 <= slot_id <= 8:
            self._focused_slot = slot_id

    def _on_env_source_changed(self, slot_id: int, source: int):
        """Handle env_source changes - refresh overlay if visible."""
        if (self.main._keyboard_overlay is not None and
            self.main._keyboard_overlay.isVisible()):
            self.main._keyboard_overlay._update_slot_buttons()

    def _on_bpm_changed(self, bpm: int):
        """Handle BPM changes - notify overlay for ARP clock sync."""
        if (self.main._keyboard_overlay is not None and
            self.main._keyboard_overlay.isVisible()):
            self.main._keyboard_overlay.notify_bpm_changed(float(bpm))

    def _get_current_bpm(self) -> float:
        """Get current BPM from main frame's BPM display or master_bpm."""
        if hasattr(self.main, 'bpm_display') and self.main.bpm_display is not None:
            return float(self.main.bpm_display.get_bpm())
        elif hasattr(self.main, 'master_bpm'):
            return float(self.main.master_bpm)
        return 120.0  # Default

    def _toggle_keyboard_mode(self):
        """Toggle the keyboard overlay for QWERTY-to-MIDI input."""
        print(f"[KB] _toggle_keyboard_mode called, overlay={self.main._keyboard_overlay}")
        if self.main._keyboard_overlay is not None and self.main._keyboard_overlay.isVisible():
            print("[KB] Dismissing existing overlay")
            self.main._keyboard_overlay._dismiss()
            return

        focus_widget = QApplication.focusWidget()
        print(f"[KB] focus_widget={focus_widget}")
        if focus_widget is not None:
            from PyQt5.QtWidgets import QLineEdit, QTextEdit, QSpinBox
            if isinstance(focus_widget, (QLineEdit, QTextEdit, QSpinBox)):
                print("[KB] Skipping - focus on text input")
                return

        if self.main._keyboard_overlay is None:
            print("[KB] Creating new KeyboardOverlay")
            self.main._keyboard_overlay = KeyboardOverlay(
                parent=self.main,
                send_note_on_fn=self._send_midi_note_on,
                send_note_off_fn=self._send_midi_note_off,
                send_all_notes_off_fn=self._send_all_notes_off,
                get_focused_slot_fn=self._get_focused_slot,
                is_slot_midi_mode_fn=self._is_slot_midi_mode,
                get_bpm_fn=self._get_current_bpm,
            )

        overlay_width = self.main._keyboard_overlay.width()
        x = self.main.x() + (self.main.width() - overlay_width) // 2
        y = self.main.y() + self.main.height() - self.main._keyboard_overlay.height() - 24
        self.main._keyboard_overlay.move(x, y)
        self.main._keyboard_overlay.show()
        self.main._keyboard_overlay.raise_()
        self.main._keyboard_overlay.activateWindow()
        print("[KB] Overlay shown and activated")

        # Deferred refresh mechanism (R1.1 spec):
        # Schedule refresh #1 on the next UI event-loop tick
        QTimer.singleShot(0, self._deferred_refresh_overlay)
        # Schedule refresh #2 at +100ms
        QTimer.singleShot(100, self._deferred_refresh_overlay)

    def _deferred_refresh_overlay(self):
        """Deferred refresh for slot button states after overlay opens."""
        if (self.main._keyboard_overlay is not None and
            self.main._keyboard_overlay.isVisible()):
            self.main._keyboard_overlay._update_slot_buttons()

    def _send_midi_note_on(self, slot: int, note: int, velocity: int):
        """Send MIDI note-on via OSC. Slot is 0-indexed."""
        if self.main.osc is not None and self.main.osc.client is not None:
            self.main.osc.client.send_message(f"/noise/slot/{slot}/midi/note_on", [note, velocity])

    def _send_midi_note_off(self, slot: int, note: int):
        """Send MIDI note-off via OSC. Slot is 0-indexed."""
        if self.main.osc is not None and self.main.osc.client is not None:
            self.main.osc.client.send_message(f"/noise/slot/{slot}/midi/note_off", [note])

    def _send_all_notes_off(self, slot: int):
        if self.main.osc is not None and self.main.osc.client is not None:
            self.main.osc.client.send_message(f"/noise/slot/{slot}/midi/all_notes_off", [])

    def _get_focused_slot(self) -> int:
        """Return currently focused slot (1-indexed for UI)."""
        return self._focused_slot

    def _is_slot_midi_mode(self, slot_id: int) -> bool:
        """
        Check if slot is in MIDI envelope mode. Slot is 1-indexed (UI).

        Per R1.1 spec, MIDI-mode rules:
        - slot.env_source == 2, OR
        - slot.env_source is a string equal to "MIDI" case-insensitively
        """
        if slot_id < 1 or slot_id > 8:
            return False

        # Get slot from grid (slots dict is keyed by 1-indexed slot_id)
        slot = self.main.generator_grid.slots.get(slot_id)
        if slot is None:
            return False  # Slot not yet available

        env_source = slot.env_source

        # Check for MIDI mode (env_source == 2 or "MIDI")
        if isinstance(env_source, int):
            return env_source == 2
        elif isinstance(env_source, str):
            return env_source.upper() == "MIDI"

        return False
