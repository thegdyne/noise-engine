"""
KeyboardController - Handles QWERTY keyboard overlay for MIDI input.

Extracted from MainFrame as Phase 7 of the god-file refactor.
Method names intentionally unchanged from MainFrame for wrapper compatibility.
"""
from __future__ import annotations

from PyQt5.QtWidgets import QApplication

from src.gui.keyboard_overlay import KeyboardOverlay
from src.utils.logger import logger


class KeyboardController:
    """Handles QWERTY keyboard overlay for MIDI input."""
    
    def __init__(self, main_frame):
        self.main = main_frame

    def _toggle_keyboard_mode(self):
        """Toggle the keyboard overlay for QWERTY-to-MIDI input."""
        if self.main._keyboard_overlay is not None and self.main._keyboard_overlay.isVisible():
            self.main._keyboard_overlay._dismiss()
            return
        
        focus_widget = QApplication.focusWidget()
        if focus_widget is not None:
            from PyQt5.QtWidgets import QLineEdit, QTextEdit, QSpinBox
            if isinstance(focus_widget, (QLineEdit, QTextEdit, QSpinBox)):
                return
        
        if self.main._keyboard_overlay is None:
            self.main._keyboard_overlay = KeyboardOverlay(
                parent=self.main,
                send_note_on_fn=self._send_midi_note_on,
                send_note_off_fn=self._send_midi_note_off,
                send_all_notes_off_fn=self._send_all_notes_off,
                get_focused_slot_fn=self._get_focused_slot,
                is_slot_midi_mode_fn=self._is_slot_midi_mode,
            )
        
        overlay_width = self.main._keyboard_overlay.width()
        x = self.main.x() + (self.main.width() - overlay_width) // 2
        y = self.main.y() + self.main.height() - self.main._keyboard_overlay.height() - 24
        self.main._keyboard_overlay.move(x, y)
        self.main._keyboard_overlay.show()
        self.main._keyboard_overlay.raise_()
        self.main._keyboard_overlay.activateWindow()

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
        return 1

    def _is_slot_midi_mode(self, slot_id: int) -> bool:
        """Check if slot is in MIDI envelope mode. Slot is 1-indexed (UI)."""
        if slot_id < 1 or slot_id > 8:
            return False
        slot = self.main.generator_grid.slots[slot_id]
        return slot.env_source == 2 or slot.env_source == "MIDI"
