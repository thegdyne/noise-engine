"""
Keyboard Mode Overlay - QWERTY keyboard as MIDI input.

CMD+K (macOS) / Ctrl+K (Win/Linux) toggles overlay.
Keys map to piano notes (Logic-style layout).
Z/X for octave shift. ESC dismisses.
"""

from PyQt5.QtCore import Qt, QPoint, QEvent
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QButtonGroup, QFrame, QApplication
)
from PyQt5.QtGui import QFont

from .theme import COLORS, FONT_FAMILY

# Key → semitone offset from C (within current octave span)
KEY_TO_SEMITONE = {
    # White keys (bottom row) - C D E F G A B C D E
    Qt.Key_A: 0,
    Qt.Key_S: 2,
    Qt.Key_D: 4,
    Qt.Key_F: 5,
    Qt.Key_G: 7,
    Qt.Key_H: 9,
    Qt.Key_J: 11,
    Qt.Key_K: 12,
    Qt.Key_L: 14,
    Qt.Key_Semicolon: 16,
    # Black keys (top row) - C# D# F# G# A# C# D#
    Qt.Key_W: 1,
    Qt.Key_E: 3,
    Qt.Key_T: 6,
    Qt.Key_Y: 8,
    Qt.Key_U: 10,
    Qt.Key_O: 13,
    Qt.Key_P: 15,
}

OCTAVE_KEYS = {
    Qt.Key_Z: -1,
    Qt.Key_X: +1,
}

# Display labels for keys
WHITE_KEYS = ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', ';']
BLACK_KEYS = ['W', 'E', '', 'T', 'Y', 'U', '', 'O', 'P']
NOTE_NAMES = ['C', 'D', 'E', 'F', 'G', 'A', 'B', 'C', 'D', 'E']


class KeyboardOverlay(QWidget):
    """
    QWERTY keyboard overlay for MIDI note input.
    
    Slot indices:
    - UI uses 1-8 (matches generator slot labels)
    - OSC uses 0-7 (internal indexing)
    - Conversion happens in send methods
    
    Usage:
        overlay = KeyboardOverlay(parent, send_note_on, send_note_off, 
                                  send_all_notes_off, get_focused_slot, is_slot_midi_mode)
        overlay.toggle()
    """
    
    def __init__(self, parent, send_note_on_fn, send_note_off_fn, 
                 send_all_notes_off_fn, get_focused_slot_fn, is_slot_midi_mode_fn):
        super().__init__(parent)
        
        # Callbacks - these expect 0-indexed slot IDs
        self._send_note_on = send_note_on_fn
        self._send_note_off = send_note_off_fn
        self._send_all_notes_off = send_all_notes_off_fn
        # These return/accept 1-indexed slot IDs
        self._get_focused_slot = get_focused_slot_fn
        self._is_slot_midi_mode = is_slot_midi_mode_fn
        
        # State - internally uses 1-indexed slot IDs (like UI)
        self._octave = 4
        self._velocity = 100
        self._pressed: dict[int, int] = {}  # qt_key -> midi_note
        self._target_slots: set[int] = set()  # 1-8 (UI indexed)
        
        # Dragging state
        self._drag_pos: QPoint | None = None
        
        # UI elements
        self._key_buttons: dict[int, QPushButton] = {}
        self._slot_buttons: list[QPushButton] = []
        self._octave_label: QLabel = None
        self._velocity_buttons: list[QPushButton] = []
        
        self._setup_ui()
        self._apply_style()
        
        # Start hidden
        self.hide()
        
        # Install event filter for window deactivation
        QApplication.instance().installEventFilter(self)
    
    def _setup_ui(self):
        """Build the overlay UI."""
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating, False)
        self.setFixedSize(520, 280)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header (draggable)
        header = self._create_header()
        layout.addWidget(header)
        
        # Keyboard area
        keyboard = self._create_keyboard()
        layout.addWidget(keyboard)
        
        # Octave controls
        octave_row = self._create_octave_controls()
        layout.addWidget(octave_row)
        
        # Target slots
        targets = self._create_target_slots()
        layout.addWidget(targets)
    
    def _create_header(self) -> QFrame:
        """Create draggable header with title, velocity selector, octave display."""
        header = QFrame()
        header.setObjectName("keyboard_header")
        header.setFixedHeight(36)
        header.setCursor(Qt.OpenHandCursor)
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(12, 0, 12, 0)
        
        # Drag handle + title
        title = QLabel("≡ KEYBOARD")
        title.setFont(QFont(FONT_FAMILY, 11, QFont.Bold))
        layout.addWidget(title)
        
        layout.addStretch()
        
        # Velocity selector
        vel_label = QLabel("Vel:")
        vel_label.setFont(QFont(FONT_FAMILY, 10))
        layout.addWidget(vel_label)
        
        vel_group = QButtonGroup(self)
        for vel in [64, 100, 127]:
            btn = QPushButton(str(vel))
            btn.setCheckable(True)
            btn.setFixedSize(36, 24)
            btn.setFont(QFont(FONT_FAMILY, 9))
            btn.clicked.connect(lambda checked, v=vel: self._set_velocity(v))
            vel_group.addButton(btn)
            self._velocity_buttons.append(btn)
            layout.addWidget(btn)
            if vel == 100:
                btn.setChecked(True)
        
        layout.addSpacing(16)
        
        # Octave display
        oct_title = QLabel("Oct:")
        oct_title.setFont(QFont(FONT_FAMILY, 10))
        layout.addWidget(oct_title)
        
        self._octave_label = QLabel(str(self._octave))
        self._octave_label.setFont(QFont(FONT_FAMILY, 12, QFont.Bold))
        self._octave_label.setFixedWidth(24)
        layout.addWidget(self._octave_label)
        
        # Make header draggable
        header.mousePressEvent = self._header_mouse_press
        header.mouseMoveEvent = self._header_mouse_move
        header.mouseReleaseEvent = self._header_mouse_release
        
        return header
    
    def _create_keyboard(self) -> QFrame:
        """Create the piano keyboard visualization."""
        keyboard = QFrame()
        keyboard.setObjectName("keyboard_keys")
        
        layout = QVBoxLayout(keyboard)
        layout.setContentsMargins(16, 12, 16, 8)
        layout.setSpacing(4)
        
        # Black keys row
        black_row = QHBoxLayout()
        black_row.setSpacing(4)
        black_row.addSpacing(20)  # Offset for piano layout
        
        for i, label in enumerate(BLACK_KEYS):
            if label:
                btn = QPushButton(label)
                btn.setFixedSize(36, 40)
                btn.setObjectName("black_key")
                btn.setFont(QFont(FONT_FAMILY, 10, QFont.Bold))
                # Map label to Qt key
                qt_key = getattr(Qt, f"Key_{label}", None)
                if qt_key:
                    self._key_buttons[qt_key] = btn
            else:
                btn = QWidget()
                btn.setFixedSize(36, 40)
            black_row.addWidget(btn)
        
        black_row.addStretch()
        layout.addLayout(black_row)
        
        # White keys row
        white_row = QHBoxLayout()
        white_row.setSpacing(4)
        
        for i, label in enumerate(WHITE_KEYS):
            btn = QPushButton(f"{label}\n{NOTE_NAMES[i]}")
            btn.setFixedSize(44, 56)
            btn.setObjectName("white_key")
            btn.setFont(QFont(FONT_FAMILY, 9))
            # Map label to Qt key
            if label == ';':
                qt_key = Qt.Key_Semicolon
            else:
                qt_key = getattr(Qt, f"Key_{label}", None)
            if qt_key:
                self._key_buttons[qt_key] = btn
            white_row.addWidget(btn)
        
        white_row.addStretch()
        layout.addLayout(white_row)
        
        return keyboard
    
    def _create_octave_controls(self) -> QFrame:
        """Create octave up/down display."""
        frame = QFrame()
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 4, 16, 4)
        
        z_label = QLabel("[Z] Oct-")
        z_label.setFont(QFont(FONT_FAMILY, 10))
        layout.addWidget(z_label)
        
        layout.addSpacing(24)
        
        x_label = QLabel("[X] Oct+")
        x_label.setFont(QFont(FONT_FAMILY, 10))
        layout.addWidget(x_label)
        
        layout.addStretch()
        
        return frame
    
    def _create_target_slots(self) -> QFrame:
        """Create target slot selection row."""
        frame = QFrame()
        frame.setObjectName("keyboard_targets")
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 8, 16, 12)
        
        label = QLabel("Target:")
        label.setFont(QFont(FONT_FAMILY, 10))
        layout.addWidget(label)
        
        layout.addSpacing(8)
        
        # Slots 1-8 (UI uses 1-indexed)
        for i in range(1, 9):
            btn = QPushButton(str(i))
            btn.setCheckable(True)
            btn.setFixedSize(32, 28)
            btn.setFont(QFont(FONT_FAMILY, 10, QFont.Bold))
            btn.clicked.connect(lambda checked, slot=i: self._toggle_target_slot(slot))
            self._slot_buttons.append(btn)
            layout.addWidget(btn)
        
        layout.addStretch()
        
        return frame
    
    def _apply_style(self):
        """Apply dark theme styling."""
        self.setStyleSheet(f"""
            KeyboardOverlay {{
                background: {COLORS['background']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
            
            #keyboard_header {{
                background: {COLORS['background_highlight']};
                border-bottom: 1px solid {COLORS['border']};
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }}
            
            #keyboard_header QLabel {{
                color: {COLORS['text_bright']};
            }}
            
            #keyboard_header QPushButton {{
                background: {COLORS['background']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 4px;
                color: {COLORS['text']};
            }}
            
            #keyboard_header QPushButton:checked {{
                background: {COLORS['selected']};
                border-color: {COLORS['selected']};
                color: {COLORS['background']};
            }}
            
            #keyboard_keys {{
                background: {COLORS['background']};
            }}
            
            #white_key {{
                background: #e8e8e8;
                border: 1px solid #999;
                border-radius: 4px;
                color: #333;
            }}
            
            #white_key:pressed, #white_key[pressed="true"] {{
                background: {COLORS['selected']};
                border-color: {COLORS['selected_dim']};
            }}
            
            #black_key {{
                background: #333;
                border: 1px solid #555;
                border-radius: 4px;
                color: #ccc;
            }}
            
            #black_key:pressed, #black_key[pressed="true"] {{
                background: {COLORS['selected']};
                border-color: {COLORS['selected_dim']};
                color: #000;
            }}
            
            #keyboard_targets {{
                background: {COLORS['background']};
                border-top: 1px solid {COLORS['border']};
            }}
            
            #keyboard_targets QLabel {{
                color: {COLORS['text']};
            }}
            
            #keyboard_targets QPushButton {{
                background: {COLORS['background_highlight']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 4px;
                color: {COLORS['text_dim']};
            }}
            
            #keyboard_targets QPushButton:checked {{
                background: {COLORS['selected']};
                border-color: {COLORS['selected_dim']};
                color: {COLORS['background']};
            }}
            
            #keyboard_targets QPushButton:disabled {{
                background: {COLORS['background']};
                border-color: {COLORS['border']};
                color: {COLORS['border']};
            }}
            
            QLabel {{
                color: {COLORS['text']};
            }}
        """)
    
    # ─────────────────────────────────────────────────────────────────
    # Header Dragging
    # ─────────────────────────────────────────────────────────────────
    
    def _header_mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def _header_mouse_move(self, event):
        if self._drag_pos is not None and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()
    
    def _header_mouse_release(self, event):
        self._drag_pos = None
        event.accept()
    
    # ─────────────────────────────────────────────────────────────────
    # State Management
    # ─────────────────────────────────────────────────────────────────
    
    def _set_velocity(self, vel: int):
        self._velocity = vel
    
    def _toggle_target_slot(self, slot: int):
        """Toggle target slot. slot is 1-indexed (UI)."""
        if slot in self._target_slots:
            self._target_slots.discard(slot)
        else:
            self._target_slots.add(slot)
    
    def _update_slot_buttons(self):
        """Update slot button states based on MIDI mode."""
        focused = self._get_focused_slot()  # Returns 1-8
        self._target_slots.clear()
        
        for i, btn in enumerate(self._slot_buttons):
            slot_id = i + 1  # 1-indexed
            is_midi = self._is_slot_midi_mode(slot_id)
            btn.setEnabled(is_midi)
            
            # Auto-select focused slot if it's in MIDI mode
            if slot_id == focused and is_midi:
                btn.setChecked(True)
                self._target_slots.add(slot_id)
            else:
                btn.setChecked(False)
        
        # If focused slot wasn't MIDI mode, select first available
        if not self._target_slots:
            for slot_id in range(1, 9):
                if self._is_slot_midi_mode(slot_id):
                    self._slot_buttons[slot_id - 1].setChecked(True)
                    self._target_slots.add(slot_id)
                    break
    
    # ─────────────────────────────────────────────────────────────────
    # Toggle / Show / Hide
    # ─────────────────────────────────────────────────────────────────
    
    def toggle(self):
        """Toggle overlay visibility."""
        if self.isVisible():
            self._dismiss()
        else:
            self._show_overlay()
    
    def _show_overlay(self):
        """Show and activate the overlay."""
        # Update slot buttons based on current MIDI mode states
        self._update_slot_buttons()
        
        # Position at bottom-center of parent, 24px margin
        if self.parent():
            parent = self.parent()
            x = (parent.width() - self.width()) // 2
            y = parent.height() - self.height() - 24
            self.move(parent.mapToGlobal(QPoint(x, y)))
        
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.ActiveWindowFocusReason)
        self.grabKeyboard()
    
    def _dismiss(self):
        """Hide overlay and clean up."""
        # Send all_notes_off to ALL slots (0-7 for OSC)
        for osc_slot in range(8):
            self._send_all_notes_off(osc_slot)
        
        self._pressed.clear()
        
        # Release keyboard before hiding
        self.releaseKeyboard()
        self.hide()
    
    # ─────────────────────────────────────────────────────────────────
    # Key Event Handling
    # ─────────────────────────────────────────────────────────────────
    
    def keyPressEvent(self, event):
        """Handle key press - trigger notes."""
        # ESC dismisses
        if event.key() == Qt.Key_Escape:
            self._dismiss()
            event.accept()
            return
        
        # Ignore auto-repeat
        if event.isAutoRepeat():
            event.accept()
            return
        
        key = event.key()
        
        # Octave change
        if key in OCTAVE_KEYS:
            self._handle_octave_change(OCTAVE_KEYS[key])
            event.accept()
            return
        
        # Note key
        if key in KEY_TO_SEMITONE and key not in self._pressed:
            semitone = KEY_TO_SEMITONE[key]
            midi_note = self._compute_midi_note(semitone)
            
            if 0 <= midi_note <= 127:
                self._pressed[key] = midi_note
                self._send_note_on_to_targets(midi_note)
                self._update_key_visual(key, True)
        
        event.accept()
    
    def keyReleaseEvent(self, event):
        """Handle key release - stop notes."""
        # Ignore auto-repeat
        if event.isAutoRepeat():
            event.accept()
            return
        
        key = event.key()
        
        # Release note
        if key in self._pressed:
            midi_note = self._pressed.pop(key)
            self._send_note_off_to_targets(midi_note)
            self._update_key_visual(key, False)
        
        event.accept()
    
    def _compute_midi_note(self, semitone: int) -> int:
        """Compute MIDI note from semitone offset and current octave."""
        # MIDI note = (octave + 1) * 12 + semitone
        return (self._octave + 1) * 12 + semitone
    
    def _handle_octave_change(self, delta: int):
        """Handle octave up/down with held note re-triggering."""
        new_octave = max(0, min(7, self._octave + delta))
        
        if new_octave == self._octave:
            return
        
        # Re-pitch all held notes
        for key, old_note in list(self._pressed.items()):
            # Note off for old pitch
            self._send_note_off_to_targets(old_note)
            
            # Compute new pitch
            semitone = KEY_TO_SEMITONE[key]
            new_note = (new_octave + 1) * 12 + semitone
            
            if 0 <= new_note <= 127:
                self._pressed[key] = new_note
                self._send_note_on_to_targets(new_note)
            else:
                # Note went out of range
                del self._pressed[key]
                self._update_key_visual(key, False)
        
        self._octave = new_octave
        self._octave_label.setText(str(self._octave))
    
    def _send_note_on_to_targets(self, note: int):
        """Send note_on to all target slots."""
        for ui_slot in self._target_slots:
            osc_slot = ui_slot - 1  # Convert 1-8 to 0-7
            self._send_note_on(osc_slot, note, self._velocity)
    
    def _send_note_off_to_targets(self, note: int):
        """Send note_off to all target slots."""
        for ui_slot in self._target_slots:
            osc_slot = ui_slot - 1  # Convert 1-8 to 0-7
            self._send_note_off(osc_slot, note)
    
    def _update_key_visual(self, qt_key: int, pressed: bool):
        """Update visual state of a key button."""
        if qt_key in self._key_buttons:
            btn = self._key_buttons[qt_key]
            btn.setProperty("pressed", "true" if pressed else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
    
    # ─────────────────────────────────────────────────────────────────
    # Window Deactivation Handling
    # ─────────────────────────────────────────────────────────────────
    
    def eventFilter(self, obj, event):
        """Handle app/window deactivation."""
        if self.isVisible():
            if event.type() in (QEvent.ApplicationDeactivate, QEvent.WindowDeactivate):
                self._dismiss()
        return super().eventFilter(obj, event)
    
    def focusOutEvent(self, event):
        """Handle focus loss."""
        # Only dismiss if we lost focus to something outside our window
        if self.isVisible():
            self._dismiss()
        super().focusOutEvent(event)
    
    def closeEvent(self, event):
        """Ensure cleanup on close."""
        self._dismiss()
        super().closeEvent(event)
