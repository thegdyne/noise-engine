"""
BPM Display Component
80s-style digital LED display like TR-909
"""

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from .theme import COLORS


class BPMDisplay(QWidget):
    """Digital BPM display with increment/decrement buttons."""
    
    bpm_changed = pyqtSignal(int)
    
    def __init__(self, initial_bpm=120, parent=None):
        super().__init__(parent)
        self.bpm = initial_bpm
        self.min_bpm = 20
        self.max_bpm = 300
        self.setup_ui()
        
    def setup_ui(self):
        """Create the display."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(3)
        
        # Decrement button
        self.dec_btn = QPushButton("◀")
        self.dec_btn.setFixedSize(24, 30)
        self.dec_btn.setFont(QFont('Helvetica', 10))
        self.dec_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['background_light']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['border']};
            }}
        """)
        self.dec_btn.clicked.connect(self.decrement)
        self.dec_btn.setAutoRepeat(True)
        self.dec_btn.setAutoRepeatDelay(300)
        self.dec_btn.setAutoRepeatInterval(50)
        layout.addWidget(self.dec_btn)
        
        # Digital display
        display_frame = QWidget()
        display_frame.setStyleSheet(f"""
            QWidget {{
                background-color: #0a0a0a;
                border: 2px solid {COLORS['border']};
                border-radius: 4px;
            }}
        """)
        display_layout = QVBoxLayout(display_frame)
        display_layout.setContentsMargins(8, 4, 8, 4)
        display_layout.setSpacing(0)
        
        # BPM label (small)
        bpm_label = QLabel("BPM")
        bpm_label.setFont(QFont('Helvetica', 7))
        bpm_label.setAlignment(Qt.AlignCenter)
        bpm_label.setStyleSheet("color: #ff3333; background: transparent; border: none;")
        display_layout.addWidget(bpm_label)
        
        # Digital number display
        self.display = QLabel(f"{self.bpm:03d}")
        self.display.setFont(QFont('DS-Digital', 32, QFont.Bold))
        self.display.setAlignment(Qt.AlignCenter)
        self.display.setStyleSheet("""
            color: #ff3333;
            background: transparent;
            border: none;
            font-family: 'Courier New', 'DS-Digital', monospace;
            letter-spacing: 2px;
        """)
        self.display.setMinimumWidth(80)
        display_layout.addWidget(self.display)
        
        layout.addWidget(display_frame)
        
        # Increment button
        self.inc_btn = QPushButton("▶")
        self.inc_btn.setFixedSize(24, 30)
        self.inc_btn.setFont(QFont('Helvetica', 10))
        self.inc_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['background_light']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['border']};
            }}
        """)
        self.inc_btn.clicked.connect(self.increment)
        self.inc_btn.setAutoRepeat(True)
        self.inc_btn.setAutoRepeatDelay(300)
        self.inc_btn.setAutoRepeatInterval(50)
        layout.addWidget(self.inc_btn)
        
    def increment(self):
        """Increase BPM by 1."""
        if self.bpm < self.max_bpm:
            self.bpm += 1
            self.update_display()
            self.bpm_changed.emit(self.bpm)
            
    def decrement(self):
        """Decrease BPM by 1."""
        if self.bpm > self.min_bpm:
            self.bpm -= 1
            self.update_display()
            self.bpm_changed.emit(self.bpm)
            
    def update_display(self):
        """Update the digital display."""
        self.display.setText(f"{self.bpm:03d}")
        
    def set_bpm(self, bpm):
        """Set BPM value."""
        self.bpm = max(self.min_bpm, min(self.max_bpm, bpm))
        self.update_display()
        
    def get_bpm(self):
        """Get current BPM."""
        return self.bpm
        
    def wheelEvent(self, event):
        """Handle mouse wheel for BPM adjustment."""
        delta = event.angleDelta().y()
        if delta > 0:
            self.increment()
        elif delta < 0:
            self.decrement()
