"""
KeyboardController - Handles QWERTY keyboard overlay for MIDI input.

Extracted from MainFrame as Phase 7 of the god-file refactor.
Method names intentionally unchanged from MainFrame for wrapper compatibility.

R1.1: Added focused slot tracking and deferred refresh mechanism.
R1.2: Added ARP support with BPM integration.
R1.3: Added application-level event filter for global keyboard capture.
"""
from __future__ import annotations

from PyQt5.QtWidgets import QApplication, QLineEdit, QTextEdit
from PyQt5.QtCore import QTimer, QObject, QEvent

from src.gui.keyboard_overlay import KeyboardOverlay
from src.utils.logger import logger


class KeyboardEventFilter(QObject):
    """
    Application-level event filter that routes keyboard events to overlay.

    This allows the keyboard overlay to receive key events even when
    the user clicks on the main UI, without requiring the overlay to have focus.
    """

    def __init__(self, controller: 'KeyboardController'):
        super().__init__()
        self._controller = controller

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Intercept key events and route to keyboard overlay if visible."""
        # Only intercept KeyPress and KeyRelease
        if event.type() not in (QEvent.KeyPress, QEvent.KeyRelease):
            return False

        # Check if overlay exists and is visible
        overlay = self._controller.main._keyboard_overlay
        if overlay is None or not overlay.isVisible():
            return False

        # Don't intercept if focus is on a text input widget
        focus_widget = QApplication.focusWidget()
        if focus_widget is not None:
            if isinstance(focus_widget, (QLineEdit, QTextEdit)):
                return False

        # Route the event to the overlay
        if event.type() == QEvent.KeyPress:
            overlay.keyPressEvent(event)
        else:
            overlay.keyReleaseEvent(event)

        # Mark event as handled to prevent further processing
        return True


class KeyboardController:
    """Handles QWERTY keyboard overlay for MIDI input."""

    def __init__(self, main_frame):
        self.main = main_frame
        self._focused_slot = 1  # Track last-focused slot (1-indexed)

        # Install application-level event filter for global keyboard capture
        # This allows the keyboard overlay to work even when clicking on main UI
        self._event_filter = KeyboardEventFilter(self)
        QApplication.instance().installEventFilter(self._event_filter)

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
        if self.main._keyboard_overlay is not None and self.main._keyboard_overlay.isVisible():
            self.main._keyboard_overlay._dismiss()
            return

        focus_widget = QApplication.focusWidget()
        if focus_widget is not None:
            # Only skip for actual text entry widgets, not spinboxes
            if isinstance(focus_widget, (QLineEdit, QTextEdit)):
                return

        if self.main._keyboard_overlay is None:
            self.main._keyboard_overlay = KeyboardOverlay(
                parent=self.main,
                send_note_on_fn=self._send_midi_note_on,
                send_note_off_fn=self._send_midi_note_off,
                send_all_notes_off_fn=self._send_all_notes_off,
                get_focused_slot_fn=self._get_focused_slot,
                is_slot_midi_mode_fn=self._is_slot_midi_mode,
                get_bpm_fn=self._get_current_bpm,
            )

        # Auto-switch focused slot to MIDI mode so keyboard works immediately
        self._ensure_focused_slot_midi()

        overlay_width = self.main._keyboard_overlay.width()
        x = self.main.x() + (self.main.width() - overlay_width) // 2
        y = self.main.y() + self.main.height() - self.main._keyboard_overlay.height() - 24
        self.main._keyboard_overlay.move(x, y)
        self.main._keyboard_overlay.show()
        self.main._keyboard_overlay.raise_()
        self.main._keyboard_overlay.activateWindow()

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

    def _ensure_focused_slot_midi(self):
        """Auto-switch focused slot to MIDI mode so keyboard works immediately."""
        slot_id = self._focused_slot
        if self._is_slot_midi_mode(slot_id):
            return  # Already MIDI

        slot = self.main.generator_grid.slots.get(slot_id)
        if slot is None:
            return

        # Switch ENV source to MIDI (index 2)
        slot.env_btn.blockSignals(True)
        slot.env_btn.set_index(2)
        slot.env_btn.blockSignals(False)
        slot.on_env_source_changed("MIDI")

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
