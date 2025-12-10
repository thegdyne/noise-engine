"""
Modulation Sources Component
LFOs and other modulation sources
"""

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFrame
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from .theme import COLORS, button_style, MONO_FONT
from .widgets import DragSlider
from src.config import SIZES, BPM_DEFAULT


class LFOWidget(QWidget):
    """Individual LFO control."""
    
    rate_changed = pyqtSignal(int, float)
    waveform_changed = pyqtSignal(int, str)
    
    def __init__(self, lfo_id, parent=None):
        super().__init__(parent)
        self.lfo_id = lfo_id
        self.waveform = "SIN"
        self.master_bpm = BPM_DEFAULT
        self.setup_ui()
        
    def setup_ui(self):
        """Create LFO widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)
        
        # Title
        title = QLabel(f"LFO {self.lfo_id}")
        title.setFont(QFont('Helvetica', 9, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {COLORS['text_bright']};")
        layout.addWidget(title)
        
        # Waveform button
        self.wave_btn = QPushButton(self.waveform)
        self.wave_btn.setFixedSize(*SIZES['button_large'])
        self.wave_btn.setFont(QFont(MONO_FONT, 8))
        self.wave_btn.setStyleSheet(button_style('enabled'))
        self.wave_btn.clicked.connect(self.cycle_waveform)
        layout.addWidget(self.wave_btn, alignment=Qt.AlignCenter)
        
        # Vertical rate slider
        self.rate_slider = DragSlider()
        self.rate_slider.setMinimumHeight(SIZES['slider_height_small'])
        self.rate_slider.valueChanged.connect(self.on_rate_changed)
        layout.addWidget(self.rate_slider, alignment=Qt.AlignCenter)
        
        # Rate label
        self.rate_label = QLabel("5.0 Hz")
        self.rate_label.setFont(QFont(MONO_FONT, 8))
        self.rate_label.setAlignment(Qt.AlignCenter)
        self.rate_label.setStyleSheet(f"color: {COLORS['text']};")
        layout.addWidget(self.rate_label)
        
        self.setFixedWidth(SIZES['lfo_widget_width'])
        self.setStyleSheet(f"""
            LFOWidget {{
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                background-color: {COLORS['background']};
            }}
        """)
        
    def cycle_waveform(self):
        """Cycle through waveforms."""
        waveforms = ["SIN", "SAW", "SQR", "S&H"]
        idx = waveforms.index(self.waveform)
        self.waveform = waveforms[(idx + 1) % len(waveforms)]
        self.wave_btn.setText(self.waveform)
        self.waveform_changed.emit(self.lfo_id, self.waveform)
        
    def on_rate_changed(self, value):
        """Handle rate slider change."""
        hz = (value / 1000.0) * 10  # 0-10 Hz
        self.rate_label.setText(f"{hz:.1f} Hz")
        self.rate_changed.emit(self.lfo_id, value / 1000.0)
        
    def set_master_bpm(self, bpm):
        """Update master BPM reference."""
        self.master_bpm = bpm


class ModulationSources(QWidget):
    """Container for modulation sources."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lfos = {}
        self.setup_ui()
        
    def setup_ui(self):
        """Create modulation sources panel."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        title = QLabel("MOD SOURCES")
        title.setFont(QFont('Helvetica', 10, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {COLORS['text_bright']};")
        layout.addWidget(title)
        
        lfos_layout = QHBoxLayout()
        lfos_layout.setSpacing(5)
        
        for i in range(1, 4):
            lfo = LFOWidget(i)
            lfos_layout.addWidget(lfo)
            self.lfos[i] = lfo
            
        layout.addLayout(lfos_layout)
        
    def set_master_bpm(self, bpm):
        """Update BPM for all LFOs."""
        for lfo in self.lfos.values():
            lfo.set_master_bpm(bpm)
