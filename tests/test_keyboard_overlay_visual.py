#!/usr/bin/env python3
"""
Standalone test for KeyboardOverlay.

Run from noise-engine root:
    python tests/test_keyboard_overlay_visual.py

Tests:
- Visual appearance matches spec
- Key press/release highlighting works
- Octave change works
- Velocity selection works
- Dismissal via ESC works

No OSC required - uses print statements to show what would be sent.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QKeySequence
from PyQt5.QtWidgets import QShortcut

from src.gui.keyboard_overlay import KeyboardOverlay
from src.gui.theme import COLORS


class TestWindow(QMainWindow):
    """Test harness for KeyboardOverlay."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Keyboard Overlay Test")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet(f"background: {COLORS['background']};")
        
        # Track "focused" slot for testing (1-indexed)
        self._focused_slot = 1
        
        # Slot MIDI mode states (1-indexed access)
        self._slot_midi_modes = {i: True for i in range(1, 9)}  # All slots in MIDI mode
        
        # Central widget with toggle button
        central = QWidget()
        layout = QVBoxLayout(central)
        
        info = QLabel("Keyboard Overlay Test\n\nPress Ctrl+K to toggle overlay")
        info.setFont(QFont("JetBrains Mono", 14))
        info.setStyleSheet(f"color: {COLORS['text_bright']};")
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)
        
        toggle_btn = QPushButton("Toggle Keyboard Overlay")
        toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['background_highlight']};
                color: {COLORS['text_bright']};
                border: 1px solid {COLORS['border_light']};
                padding: 12px 24px;
                font-size: 14px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background: {COLORS['selected']};
                color: {COLORS['background']};
            }}
        """)
        toggle_btn.clicked.connect(self._toggle_keyboard)
        layout.addWidget(toggle_btn, alignment=Qt.AlignCenter)
        
        self.setCentralWidget(central)
        
        # Create overlay
        self._keyboard = KeyboardOverlay(
            parent=self,
            send_note_on_fn=self._mock_note_on,
            send_note_off_fn=self._mock_note_off,
            send_all_notes_off_fn=self._mock_all_notes_off,
            get_focused_slot_fn=lambda: self._focused_slot,
            is_slot_midi_mode_fn=lambda slot_id: self._slot_midi_modes.get(slot_id, False),
        )
        
        # Shortcut
        shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        shortcut.activated.connect(self._toggle_keyboard)
    
    def _toggle_keyboard(self):
        self._keyboard.toggle()
    
    def _mock_note_on(self, slot: int, note: int, velocity: int):
        """Mock OSC send - slot is 0-indexed."""
        note_name = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'][note % 12]
        octave = (note // 12) - 1
        print(f"[OSC] /noise/slot/{slot}/midi/note_on  {note} ({note_name}{octave}) vel={velocity}")
    
    def _mock_note_off(self, slot: int, note: int):
        """Mock OSC send - slot is 0-indexed."""
        note_name = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'][note % 12]
        octave = (note // 12) - 1
        print(f"[OSC] /noise/slot/{slot}/midi/note_off {note} ({note_name}{octave})")
    
    def _mock_all_notes_off(self, slot: int):
        """Mock OSC send - slot is 0-indexed."""
        print(f"[OSC] /noise/slot/{slot}/midi/all_notes_off")


def main():
    app = QApplication(sys.argv)
    
    # Dark theme for app
    app.setStyle("Fusion")
    
    window = TestWindow()
    window.show()
    
    print("\n" + "=" * 60)
    print("KEYBOARD OVERLAY TEST")
    print("=" * 60)
    print("• Click button or press Ctrl+K to toggle overlay")
    print("• Use ASDFGHJKL; for white keys, WETYUOP for black keys")
    print("• Z = octave down, X = octave up")
    print("• ESC to dismiss")
    print("• Watch console for OSC messages")
    print("=" * 60 + "\n")
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
