"""
Modulation Sources Panel
LFOs, Chaotic LFO, Envelope with clock routing
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QComboBox)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from .clock_divider import ClockDivider


class EnvelopeAD(QWidget):
    """AD Envelope with clock routing."""
    
    clock_routing_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.clock_routing = "Off"
        self.setup_ui()
        
    def setup_ui(self):
        """Create envelope interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        title = QLabel("ENVELOPE AD")
        title_font = QFont('Helvetica', 10, QFont.Bold)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        self.clock_btn = QPushButton("CLK: Off")
        self.clock_btn.setFixedHeight(25)
        self.clock_btn.setStyleSheet("""
            QPushButton {
                background-color: #444;
                color: white;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """)
        self.clock_btn.clicked.connect(self.cycle_clock_routing)
        layout.addWidget(self.clock_btn)
        
        layout.addStretch()
        
    def cycle_clock_routing(self):
        """Cycle through clock routing options."""
        options = ["Off", "CLK", "CLK/2", "CLK/4", "CLK/8", "CLK/16"]
        current_index = options.index(self.clock_routing)
        next_index = (current_index + 1) % len(options)
        self.clock_routing = options[next_index]
        self.clock_btn.setText(f"CLK: {self.clock_routing}")
        self.clock_routing_changed.emit(self.clock_routing)
        print(f"Envelope clock routing: {self.clock_routing}")


class ModulationSources(QWidget):
    """Panel with all modulation sources."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """Create modulation sources interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        title = QLabel("MODULATION")
        title_font = QFont('Helvetica', 12, QFont.Bold)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        main_layout.addWidget(separator)
        
        self.clock_divider = ClockDivider()
        main_layout.addWidget(self.clock_divider)
        
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        main_layout.addWidget(sep2)
        
        placeholder = QLabel("LFO 1\nLFO 2\nLFO 3\nChaotic LFO\n(coming soon)")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("color: #666;")
        main_layout.addWidget(placeholder)
        
        sep3 = QFrame()
        sep3.setFrameShape(QFrame.HLine)
        main_layout.addWidget(sep3)
        
        self.envelope = EnvelopeAD()
        main_layout.addWidget(self.envelope)
        
        main_layout.addStretch()
        
    def set_master_bpm(self, bpm):
        """Update clock divider with master BPM."""
        self.clock_divider.set_master_bpm(bpm)
