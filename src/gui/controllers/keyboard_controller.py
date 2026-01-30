"""
KeyboardController - Handles QWERTY keyboard overlay for MIDI input.

Extracted from MainFrame as Phase 7 of the god-file refactor.

R1.1: Added focused slot tracking and deferred refresh mechanism.
R1.2: Added ARP support with BPM integration.
R1.3: Added application-level event filter for global keyboard capture.
R2.0: Per-slot ARP (PER_SLOT_ARP_SPEC v1.2.1).
      - Owns ArpSlotManager (8 engines, one per slot)
      - Overlay is pure view, bound via set_arp_engine()
      - Focus switching with prev_engine reference capture
      - ARP+HOLD persistence across keyboard hide/show
R3.0: SH-101 Step Sequencer + MotionManager.
      - Owns MotionManager (8 SEQ engines + mode coordination)
      - SEQ toggle in overlay with Rate, Length, REC controls
      - Step recording via QWERTY keys
"""
from __future__ import annotations

from PyQt5.QtWidgets import QApplication, QLineEdit, QTextEdit
from PyQt5.QtCore import QTimer, QObject, QEvent

from src.gui.keyboard_overlay import KeyboardOverlay
from src.gui.arp_slot_manager import ArpSlotManager
from src.gui.motion_manager import MotionManager
from src.model.sequencer import MotionMode
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
    """
    Handles QWERTY keyboard overlay for MIDI input (Per-Slot ARP v2.0).

    Owns ArpSlotManager with 8 engines. Overlay is a pure view that gets
    bound to the focused slot's engine via set_arp_engine().
    """

    def __init__(self, main_frame):
        self.main = main_frame
        self._focused_slot = 1  # Track last-focused slot (1-indexed)

        # Create ArpSlotManager (8 engines created eagerly)
        self._arp_manager = ArpSlotManager(
            send_note_on=self._send_midi_note_on,
            send_note_off=self._send_midi_note_off,
            send_all_notes_off=self._send_all_notes_off,
            get_velocity=self._get_overlay_velocity,
            get_bpm=self._get_current_bpm,
        )

        # Create MotionManager (8 SEQ engines + mode coordination)
        self._motion_manager = MotionManager(
            arp_engines=self._arp_manager.engines,
            send_note_on=self._send_midi_note_on,
            send_note_off=self._send_midi_note_off,
            get_bpm=self._get_current_bpm,
        )

        # Install application-level event filter for global keyboard capture
        self._event_filter = KeyboardEventFilter(self)
        QApplication.instance().installEventFilter(self._event_filter)

        # Connect to generator_grid slot click events if available
        if hasattr(self.main, 'generator_grid') and self.main.generator_grid is not None:
            self.main.generator_grid.generator_selected.connect(self._on_slot_selected)
            self.main.generator_grid.generator_env_source_changed.connect(self._on_env_source_changed)

        # Connect to BPM changes for ARP clock sync
        if hasattr(self.main, 'bpm_display') and self.main.bpm_display is not None:
            self.main.bpm_display.bpm_changed.connect(self._on_bpm_changed)

    # =========================================================================
    # PROPERTIES
    # =========================================================================

    @property
    def arp_manager(self) -> ArpSlotManager:
        """Access the ARP slot manager (for main_frame wiring)."""
        return self._arp_manager

    @property
    def motion_manager(self) -> MotionManager:
        """Access the MotionManager (for clock wiring)."""
        return self._motion_manager

    # =========================================================================
    # SLOT / ENV SOURCE SIGNALS
    # =========================================================================

    def _on_slot_selected(self, slot_id: int):
        """Track which slot was last selected/clicked (1-indexed)."""
        if 1 <= slot_id <= 8:
            old_focused = self._focused_slot
            self._focused_slot = slot_id

            # If overlay is visible and slot changed, switch engine
            if (self.main._keyboard_overlay is not None and
                self.main._keyboard_overlay.isVisible() and
                    slot_id != old_focused):
                self._switch_focus_to_slot(slot_id)

    def _on_env_source_changed(self, slot_id: int, source: int):
        """Handle env_source changes - refresh overlay if visible."""
        if (self.main._keyboard_overlay is not None and
                self.main._keyboard_overlay.isVisible()):
            self.main._keyboard_overlay._update_slot_buttons()

    def _on_bpm_changed(self, bpm: int):
        """Handle BPM changes - forward to all engines via manager."""
        self._arp_manager.on_bpm_changed(float(bpm))

    # =========================================================================
    # OVERLAY VELOCITY CALLBACK
    # =========================================================================

    def _get_overlay_velocity(self) -> int:
        """Get velocity from overlay (callback for ArpEngine)."""
        if self.main._keyboard_overlay is not None:
            return self.main._keyboard_overlay.get_velocity()
        return 100  # Default

    # =========================================================================
    # BPM
    # =========================================================================

    def _get_current_bpm(self) -> float:
        """Get current BPM from main frame's BPM display or master_bpm."""
        if hasattr(self.main, 'bpm_display') and self.main.bpm_display is not None:
            return float(self.main.bpm_display.get_bpm())
        elif hasattr(self.main, 'master_bpm'):
            return float(self.main.master_bpm)
        return 120.0  # Default

    # =========================================================================
    # KEYBOARD TOGGLE (Cmd+K)
    # =========================================================================

    def _toggle_keyboard_mode(self):
        """Toggle the keyboard overlay for QWERTY-to-MIDI input."""
        if self.main._keyboard_overlay is not None and self.main._keyboard_overlay.isVisible():
            self._on_keyboard_dismiss()
            return

        focus_widget = QApplication.focusWidget()
        if focus_widget is not None:
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
                on_slot_focus_changed_fn=self._on_overlay_slot_focus_changed,
                on_seq_mode_changed_fn=self._on_seq_mode_changed,
            )

        # Auto-switch focused slot to MIDI mode so keyboard works immediately
        self._ensure_focused_slot_midi()

        # Bind focused slot's engines to overlay
        slot_0idx = self._focused_slot - 1
        engine = self._arp_manager.get_engine(slot_0idx)
        self.main._keyboard_overlay.set_arp_engine(engine)

        seq_engine = self._motion_manager.get_seq_engine(slot_0idx)
        self.main._keyboard_overlay.set_seq_engine(seq_engine)

        # Sync SEQ UI state from MotionManager
        seq_active = self._motion_manager.get_mode(slot_0idx) == MotionMode.SEQ
        self.main._keyboard_overlay.sync_seq_ui_state(seq_active)

        overlay_width = self.main._keyboard_overlay.width()
        x = self.main.x() + (self.main.width() - overlay_width) // 2
        y = self.main.y() + self.main.height() - self.main._keyboard_overlay.height() - 24
        self.main._keyboard_overlay.move(x, y)
        self.main._keyboard_overlay.show()
        self.main._keyboard_overlay.raise_()

        # Deferred refresh mechanism (R1.1 spec)
        QTimer.singleShot(0, self._deferred_refresh_overlay)
        QTimer.singleShot(100, self._deferred_refresh_overlay)

    def _deferred_refresh_overlay(self):
        """Deferred refresh for slot button states after overlay opens."""
        if (self.main._keyboard_overlay is not None and
                self.main._keyboard_overlay.isVisible()):
            self.main._keyboard_overlay._update_slot_buttons()

    # =========================================================================
    # FOCUS SWITCHING (per spec v1.2.1 — Invariant #14)
    # =========================================================================

    def _on_overlay_slot_focus_changed(self, new_slot_ui: int):
        """
        Handle overlay slot button click (1-indexed).
        Called from overlay's _on_target_slot_clicked.
        """
        if new_slot_ui == self._focused_slot:
            return
        self._switch_focus_to_slot(new_slot_ui)

    def _switch_focus_to_slot(self, new_slot_ui: int):
        """
        Switch keyboard focus to a new slot (1-indexed).

        Per spec v1.2.1 Invariant #14: capture prev_engine reference BEFORE
        any iteration or mutation.
        """
        overlay = self.main._keyboard_overlay
        if overlay is None:
            self._focused_slot = new_slot_ui
            return

        # 1. Capture previous engine reference (Invariant #14)
        prev_slot = self._focused_slot
        prev_engine = self._arp_manager.get_engine(prev_slot - 1)

        # 2. Release all physical keys from previous engine
        overlay.release_physical_keys_from_engine()

        # 3. Update focused slot
        self._focused_slot = new_slot_ui

        # 4. Auto-switch new slot to MIDI mode
        self._ensure_focused_slot_midi()

        # 5. Get new slot's engines and bind to overlay
        new_0idx = new_slot_ui - 1
        new_engine = self._arp_manager.get_engine(new_0idx)
        overlay.set_arp_engine(new_engine)

        new_seq = self._motion_manager.get_seq_engine(new_0idx)
        overlay.set_seq_engine(new_seq)

        # 6. Sync SEQ UI state for new slot
        seq_active = self._motion_manager.get_mode(new_0idx) == MotionMode.SEQ
        overlay.sync_seq_ui_state(seq_active)

        # 7. Update slot button states
        overlay._update_slot_buttons()

        # 8. Previous engine continues if ARP+HOLD active (no teardown)
        logger.debug(
            f"KeyboardController: focus switched slot {prev_slot} -> {new_slot_ui}, "
            f"prev has_hold={prev_engine.has_hold}",
            component="ARP"
        )

    # =========================================================================
    # KEYBOARD DISMISS (per spec v1.2.1)
    # =========================================================================

    def _on_keyboard_dismiss(self):
        """
        Handle keyboard overlay dismissal.

        Per spec v1.2.1:
        1. Release physical keys from focused engine
        2. For each engine: if has_hold, skip; otherwise reset
        3. Unbind engine from overlay
        4. Hide overlay
        """
        overlay = self.main._keyboard_overlay
        if overlay is None:
            return

        # Overlay's _dismiss() releases physical keys and hides
        overlay._dismiss()

        # Teardown/preserve engines based on hold state and SEQ activity
        for slot in range(8):
            engine = self._arp_manager.get_engine(slot)
            mode = self._motion_manager.get_mode(slot)

            if mode == MotionMode.SEQ:
                # Preserve: SEQ keeps running (same as ARP+HOLD)
                logger.debug(
                    f"KeyboardController: preserving SEQ on slot {slot}",
                    component="SEQ"
                )
            elif engine.has_hold:
                # Preserve: ARP+HOLD keeps playing
                logger.debug(
                    f"KeyboardController: preserving ARP+HOLD on slot {slot}",
                    component="ARP"
                )
            else:
                # Teardown: nothing active, clean up
                self._motion_manager.panic_slot(slot)
                self._arp_manager.reset_slot(slot)

        # Unbind engines from overlay
        overlay.set_seq_engine(None)
        overlay.set_arp_engine(None)

    # =========================================================================
    # SEQ MODE CHANGE
    # =========================================================================

    def _on_seq_mode_changed(self, enabled: bool, slot_0idx: int):
        """
        Handle SEQ mode change from overlay.

        Args:
            enabled: True to start SEQ, False to stop
            slot_0idx: Target slot (0-indexed, from bound SeqEngine)
        """
        if enabled:
            self._motion_manager.set_mode(slot_0idx, MotionMode.SEQ)
            logger.debug(
                f"KeyboardController: SEQ enabled on slot {slot_0idx}",
                component="SEQ"
            )
        else:
            self._motion_manager.set_mode(slot_0idx, MotionMode.OFF)
            logger.debug(
                f"KeyboardController: SEQ disabled on slot {slot_0idx}",
                component="SEQ"
            )

    # =========================================================================
    # OSC SEND HELPERS
    # =========================================================================

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

    # =========================================================================
    # MIDI MODE HELPERS
    # =========================================================================

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

        slot = self.main.generator_grid.slots.get(slot_id)
        if slot is None:
            return False

        env_source = slot.env_source

        if isinstance(env_source, int):
            return env_source == 2
        elif isinstance(env_source, str):
            return env_source.upper() == "MIDI"

        return False
