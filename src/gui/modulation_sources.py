"""
Modulation Sources Component
LFOs and other modulation sources
"""

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFrame
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from .theme import COLORS, button_style, MONO_FONT
from .widgets import DragSlider, CycleButton
from src.config import SIZES, BPM_DEFAULT, LFO_WAVEFORMS, CLOCK_RATES, CLOCK_DEFAULT_INDEX


class LFOWidget(QWidget):
    """Individual LFO control."""
    
    rate_changed = pyqtSignal(int, float)
    waveform_changed = pyqtSignal(int, str)
    sync_changed = pyqtSignal(int, bool)
    clock_rate_changed = pyqtSignal(int, str)
    
    def __init__(self, lfo_id, parent=None):
        super().__init__(parent)
        self.lfo_id = lfo_id
        self.sync_enabled = False
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
        
        # Waveform button - CycleButton
        self.wave_btn = CycleButton(LFO_WAVEFORMS, initial_index=0)
        self.wave_btn.setFixedSize(*SIZES['button_large'])
        self.wave_btn.setFont(QFont(MONO_FONT, 8))
        self.wave_btn.setStyleSheet(button_style('enabled'))
        self.wave_btn.wrap = True
        self.wave_btn.value_changed.connect(self.on_waveform_changed)
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
        
        # SYNC toggle
        self.sync_btn = QPushButton("SYNC")
        self.sync_btn.setFixedSize(*SIZES['button_large'])
        self.sync_btn.setFont(QFont(MONO_FONT, 7, QFont.Bold))
        self.sync_btn.setStyleSheet(button_style('disabled'))
        self.sync_btn.clicked.connect(self.toggle_sync)
        layout.addWidget(self.sync_btn, alignment=Qt.AlignCenter)
        
        # CLK division button - CycleButton
        self.clk_btn = CycleButton(CLOCK_RATES, initial_index=CLOCK_DEFAULT_INDEX)
        self.clk_btn.setFixedSize(*SIZES['button_large'])
        self.clk_btn.setFont(QFont(MONO_FONT, 7))
        self.clk_btn.setStyleSheet(button_style('inactive'))
        self.clk_btn.wrap = False
        self.clk_btn.setEnabled(False)
        self.clk_btn.value_changed.connect(self.on_clock_rate_changed)
        layout.addWidget(self.clk_btn, alignment=Qt.AlignCenter)
        
        self.setFixedWidth(SIZES['lfo_widget_width'])
        self.setStyleSheet(f"""
            LFOWidget {{
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                background-color: {COLORS['background']};
            }}
        """)
        
    def toggle_sync(self):
        """Toggle sync on/off."""
        self.sync_enabled = not self.sync_enabled
        self.update_sync_style()
        self.sync_changed.emit(self.lfo_id, self.sync_enabled)
        
    def update_sync_style(self):
        """Update button styles based on sync state."""
        if self.sync_enabled:
            self.sync_btn.setStyleSheet(button_style('enabled'))
            self.clk_btn.setEnabled(True)
            self.clk_btn.setStyleSheet(button_style('submenu'))
            self.rate_slider.setEnabled(False)
        else:
            self.sync_btn.setStyleSheet(button_style('disabled'))
            self.clk_btn.setEnabled(False)
            self.clk_btn.setStyleSheet(button_style('inactive'))
            self.rate_slider.setEnabled(True)
        
    def on_waveform_changed(self, waveform):
        """Handle waveform button change."""
        self.waveform_changed.emit(self.lfo_id, waveform)
        
    def on_rate_changed(self, value):
        """Handle rate slider change."""
        hz = (value / 1000.0) * 10  # 0-10 Hz
        self.rate_label.setText(f"{hz:.1f} Hz")
        self.rate_changed.emit(self.lfo_id, value / 1000.0)
        
    def on_clock_rate_changed(self, rate):
        """Handle clock rate button change."""
        self.clock_rate_changed.emit(self.lfo_id, rate)
        
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
