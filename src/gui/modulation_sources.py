"""
Modulation Sources Panel
LFOs, Chaotic LFO, Envelope with clock routing
Horizontal layout to fit in bottom section
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QComboBox, QGridLayout)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont


class ClockIndicator(QWidget):
    """Single clock division indicator."""
    
    def __init__(self, label, parent=None):
        super().__init__(parent)
        self.label_text = label
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        
        self.indicator = QLabel("●")
        self.indicator.setAlignment(Qt.AlignCenter)
        self.indicator.setStyleSheet("color: #333; font-size: 14px;")
        layout.addWidget(self.indicator)
        
        label = QLabel(self.label_text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: #888; font-size: 8px;")
        layout.addWidget(label)
        
    def pulse(self):
        """Flash the indicator."""
        self.indicator.setStyleSheet("color: #44ff44; font-size: 14px;")
        QTimer.singleShot(100, lambda: self.indicator.setStyleSheet("color: #333; font-size: 14px;"))


class EnvelopeAD(QWidget):
    """Compact AD Envelope with clock routing."""
    
    clock_routing_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.clock_routing = "Off"
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)
        
        title = QLabel("ENV")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-weight: bold; font-size: 10px;")
        layout.addWidget(title)
        
        self.clock_btn = QPushButton("Off")
        self.clock_btn.setFixedSize(50, 25)
        self.clock_btn.setStyleSheet("""
            QPushButton {
                background-color: #444;
                color: white;
                border-radius: 3px;
                font-size: 9px;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """)
        self.clock_btn.clicked.connect(self.cycle_clock_routing)
        layout.addWidget(self.clock_btn, alignment=Qt.AlignCenter)
        
    def cycle_clock_routing(self):
        """Cycle through clock routing options."""
        options = ["Off", "CLK", "/2", "/4", "/8", "/16"]
        current_index = options.index(self.clock_routing)
        next_index = (current_index + 1) % len(options)
        self.clock_routing = options[next_index]
        self.clock_btn.setText(self.clock_routing)
        
        if self.clock_routing != "Off":
            self.clock_btn.setStyleSheet("""
                QPushButton {
                    background-color: #226622;
                    color: white;
                    border-radius: 3px;
                    font-size: 9px;
                }
            """)
        else:
            self.clock_btn.setStyleSheet("""
                QPushButton {
                    background-color: #444;
                    color: white;
                    border-radius: 3px;
                    font-size: 9px;
                }
            """)
        
        self.clock_routing_changed.emit(self.clock_routing)
        print(f"Envelope clock: {self.clock_routing}")


class LFOModule(QWidget):
    """Compact LFO module."""
    
    def __init__(self, lfo_id, parent=None):
        super().__init__(parent)
        self.lfo_id = lfo_id
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)
        
        title = QLabel(f"LFO{self.lfo_id}")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-weight: bold; font-size: 10px;")
        layout.addWidget(title)
        
        self.wave_btn = QPushButton("SIN")
        self.wave_btn.setFixedSize(40, 20)
        self.wave_btn.setStyleSheet("""
            QPushButton {
                background-color: #444;
                color: #aaa;
                border-radius: 2px;
                font-size: 8px;
            }
        """)
        self.wave_btn.clicked.connect(self.cycle_waveform)
        layout.addWidget(self.wave_btn, alignment=Qt.AlignCenter)
        
        self.waveform = "SIN"
        self.waveforms = ["SIN", "SAW", "SQR", "S&H"]
        
    def cycle_waveform(self):
        """Cycle through waveforms."""
        idx = self.waveforms.index(self.waveform)
        self.waveform = self.waveforms[(idx + 1) % len(self.waveforms)]
        self.wave_btn.setText(self.waveform)
        print(f"LFO{self.lfo_id} waveform: {self.waveform}")


class ModulationSources(QWidget):
    """Panel with all modulation sources - horizontal layout."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.master_bpm = 120
        self.beat_counter = 0
        self.indicators = {}
        
        self.setup_ui()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.on_beat)
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 5, 10, 5)
        main_layout.setSpacing(5)
        
        title = QLabel("MODULATION")
        title_font = QFont('Helvetica', 11, QFont.Bold)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        content = QHBoxLayout()
        content.setSpacing(10)
        
        clock_frame = QFrame()
        clock_frame.setStyleSheet("border: 1px solid #444; border-radius: 3px;")
        clock_layout = QHBoxLayout(clock_frame)
        clock_layout.setContentsMargins(5, 5, 5, 5)
        clock_layout.setSpacing(5)
        
        divisions = [("CLK", 1), ("/2", 2), ("/4", 4), ("/8", 8), ("/16", 16)]
        for label, div in divisions:
            indicator = ClockIndicator(label)
            clock_layout.addWidget(indicator)
            self.indicators[div] = indicator
            
        content.addWidget(clock_frame)
        
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.VLine)
        sep1.setStyleSheet("color: #444;")
        content.addWidget(sep1)
        
        for i in range(1, 4):
            lfo = LFOModule(i)
            content.addWidget(lfo)
            
        chaos_label = QLabel("CHAOS")
        chaos_label.setAlignment(Qt.AlignCenter)
        chaos_label.setStyleSheet("color: #666; font-size: 9px;")
        content.addWidget(chaos_label)
        
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.VLine)
        sep2.setStyleSheet("color: #444;")
        content.addWidget(sep2)
        
        self.envelope = EnvelopeAD()
        content.addWidget(self.envelope)
        
        main_layout.addLayout(content)
        
    def set_master_bpm(self, bpm):
        """Update master BPM."""
        self.master_bpm = bpm
        self.beat_counter = 0
        if bpm > 0:
            interval = int(60000 / bpm)
            self.timer.start(interval)
        else:
            self.timer.stop()
            
    def on_beat(self):
        """Called on each master beat."""
        self.beat_counter += 1
        
        for div, indicator in self.indicators.items():
            if self.beat_counter % div == 0:
                indicator.pulse()
