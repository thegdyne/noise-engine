"""
BPM Display Component
TR-909 style digital BPM display with click+drag to change value
"""

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

from .theme import COLORS, MONO_FONT, FONT_FAMILY, FONT_SIZES
from .widgets import DragValue
from src.config import BPM_DEFAULT, BPM_MIN, BPM_MAX, SIZES


class BPMDisplay(QWidget):
    """TR-909 style BPM display with drag-to-change."""
    
    bpm_changed = pyqtSignal(int)
    
    def __init__(self, initial_bpm=None, parent=None):
        super().__init__(parent)
        self.bpm = initial_bpm if initial_bpm is not None else BPM_DEFAULT
        self.setup_ui()
        
    def setup_ui(self):
        """Create BPM display."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        # Container for 909 look
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['background_dark']};
                border: 2px solid {COLORS['border_light']};
                border-radius: 4px;
            }}
        """)
        
        # Decrease button
        self.dec_btn = QPushButton("◀")
        self.dec_btn.setFixedSize(*SIZES['button_bpm'])
        self.dec_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 3px;
                font-size: {FONT_SIZES['section']}px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['background_highlight']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['border']};
            }}
        """)
        self.dec_btn.pressed.connect(self.start_decrease)
        self.dec_btn.released.connect(self.stop_repeat)
        layout.addWidget(self.dec_btn)
        
        # BPM display section (vertical stack)
        display_layout = QVBoxLayout()
        display_layout.setContentsMargins(0, 0, 0, 0)
        display_layout.setSpacing(0)
        
        # Small "BPM" label above
        bpm_label = QLabel("BPM")
        bpm_label.setFont(QFont(FONT_FAMILY, FONT_SIZES['tiny']))
        bpm_label.setAlignment(Qt.AlignCenter)
        bpm_label.setStyleSheet(f"color: {COLORS['text_label']}; background: transparent; border: none;")
        display_layout.addWidget(bpm_label)
        
        # Large draggable LED display
        self.display = DragValue(self.bpm, BPM_MIN, BPM_MAX)
        self.display.setFont(QFont(MONO_FONT, FONT_SIZES['display'], QFont.Bold))
        self.display.setAlignment(Qt.AlignCenter)
        self.display.setStyleSheet(f"""
            color: {COLORS['bpm_text']};
            background: transparent;
            border: none;
            letter-spacing: 3px;
        """)
        self.display.setToolTip("Drag up/down to change BPM\nShift + drag for fine control")
        self.display.value_changed.connect(self.on_drag_changed)
        display_layout.addWidget(self.display)
        
        layout.addLayout(display_layout)
        
        # Increase button
        self.inc_btn = QPushButton("▶")
        self.inc_btn.setFixedSize(*SIZES['button_bpm'])
        self.inc_btn.setStyleSheet(self.dec_btn.styleSheet())
        self.inc_btn.pressed.connect(self.start_increase)
        self.inc_btn.released.connect(self.stop_repeat)
        layout.addWidget(self.inc_btn)
        
        # Auto-repeat timer
        self.repeat_timer = QTimer()
        self.repeat_timer.timeout.connect(self.repeat_action)
        self.repeat_action_func = None
        
    def on_drag_changed(self, value):
        """Handle drag value change."""
        self.bpm = value
        self.bpm_changed.emit(self.bpm)
        
    def start_increase(self):
        """Start increasing BPM."""
        self.change_bpm(1)
        self.repeat_action_func = lambda: self.change_bpm(1)
        self.repeat_timer.start(300)
        
    def start_decrease(self):
        """Start decreasing BPM."""
        self.change_bpm(-1)
        self.repeat_action_func = lambda: self.change_bpm(-1)
        self.repeat_timer.start(300)
        
    def repeat_action(self):
        """Repeat the current action faster."""
        if self.repeat_action_func:
            self.repeat_action_func()
            self.repeat_timer.setInterval(50)
            
    def stop_repeat(self):
        """Stop auto-repeat."""
        self.repeat_timer.stop()
        self.repeat_action_func = None
        
    def change_bpm(self, delta):
        """Change BPM by delta."""
        self.bpm = max(BPM_MIN, min(BPM_MAX, self.bpm + delta))
        self.display.set_value(self.bpm)
        self.bpm_changed.emit(self.bpm)
        
    def set_bpm(self, bpm):
        """Set BPM programmatically."""
        self.bpm = max(BPM_MIN, min(BPM_MAX, bpm))
        self.display.set_value(self.bpm)
