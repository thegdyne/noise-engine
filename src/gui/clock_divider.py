"""
Clock Divider Component
Provides clock divisions for triggering modulation sources
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont


class ClockDivider(QWidget):
    """Clock divider showing divisions of master clock."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.master_bpm = 120
        self.beat_counters = {1: 0, 2: 0, 4: 0, 8: 0, 16: 0}
        self.indicators = {}
        
        self.setup_ui()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_clock)
        
    def setup_ui(self):
        """Create the divider interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        title = QLabel("CLOCK DIVIDER")
        title_font = QFont('Helvetica', 10, QFont.Bold)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        layout.addWidget(separator)
        
        divisions = [1, 2, 4, 8, 16]
        for div in divisions:
            div_widget = self.create_division(div)
            layout.addWidget(div_widget)
            
    def create_division(self, division):
        """Create a single division indicator."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(5)
        
        label_text = "CLK" if division == 1 else f"CLK/{division}"
        label = QLabel(label_text)
        label_font = QFont('Courier', 9, QFont.Bold)
        label.setFont(label_font)
        layout.addWidget(label)
        
        layout.addStretch()
        
        indicator = QLabel("●")
        indicator_font = QFont('Helvetica', 12)
        indicator.setFont(indicator_font)
        indicator.setStyleSheet("color: #333;")
        layout.addWidget(indicator)
        
        self.indicators[division] = indicator
        
        return widget
        
    def set_master_bpm(self, bpm):
        """Update master BPM."""
        self.master_bpm = bpm
        if self.master_bpm > 0:
            interval = int(60000 / self.master_bpm)
            self.timer.start(interval)
        else:
            self.timer.stop()
            
    def update_clock(self):
        """Called on each master beat."""
        for div in self.beat_counters.keys():
            self.beat_counters[div] += 1
            if self.beat_counters[div] >= div:
                self.beat_counters[div] = 0
                self.pulse_indicator(div)
                
    def pulse_indicator(self, division):
        """Flash indicator for a division."""
        indicator = self.indicators[division]
        indicator.setStyleSheet("color: #44ff44;")
        QTimer.singleShot(100, lambda: indicator.setStyleSheet("color: #333;"))
