"""
Modulation Sources Component
LFOs and other modulation sources - vertical layout for left panel

STATUS: Work In Progress - UI visible but not yet connected
"""

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFrame
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from .theme import COLORS, button_style, MONO_FONT, FONT_FAMILY, FONT_SIZES, wip_panel_style, wip_badge_style
from .widgets import DragSlider, CycleButton
from src.config import SIZES, BPM_DEFAULT, LFO_WAVEFORMS, CLOCK_RATES, CLOCK_DEFAULT_INDEX


class LFOWidget(QWidget):
    """Individual LFO control - horizontal layout for side panel."""
    
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
        """Create LFO widget - compact horizontal layout."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Left column - labels and buttons
        left_col = QVBoxLayout()
        left_col.setSpacing(3)
        
        # Title
        title = QLabel(f"LFO {self.lfo_id}")
        title.setFont(QFont(FONT_FAMILY, FONT_SIZES['small'], QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['text_bright']};")
        left_col.addWidget(title)
        
        # Waveform button
        self.wave_btn = CycleButton(LFO_WAVEFORMS, initial_index=0)
        self.wave_btn.setFixedSize(45, 20)
        self.wave_btn.setFont(QFont(MONO_FONT, FONT_SIZES['tiny']))
        self.wave_btn.setStyleSheet(button_style('enabled'))
        self.wave_btn.wrap = True
        self.wave_btn.value_changed.connect(self.on_waveform_changed)
        left_col.addWidget(self.wave_btn)
        
        # SYNC button
        self.sync_btn = QPushButton("SYNC")
        self.sync_btn.setFixedSize(45, 20)
        self.sync_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro'], QFont.Bold))
        self.sync_btn.setStyleSheet(button_style('disabled'))
        self.sync_btn.clicked.connect(self.toggle_sync)
        left_col.addWidget(self.sync_btn)
        
        # CLK division button
        self.clk_btn = CycleButton(CLOCK_RATES, initial_index=CLOCK_DEFAULT_INDEX)
        self.clk_btn.setFixedSize(45, 20)
        self.clk_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        self.clk_btn.setStyleSheet(button_style('inactive'))
        self.clk_btn.wrap = False
        self.clk_btn.setEnabled(False)
        self.clk_btn.value_changed.connect(self.on_clock_rate_changed)
        left_col.addWidget(self.clk_btn)
        
        left_col.addStretch()
        layout.addLayout(left_col)
        
        # Right column - rate slider
        right_col = QVBoxLayout()
        right_col.setSpacing(2)
        
        self.rate_slider = DragSlider()
        self.rate_slider.setMinimumHeight(70)
        self.rate_slider.valueChanged.connect(self.on_rate_changed)
        right_col.addWidget(self.rate_slider, alignment=Qt.AlignCenter)
        
        self.rate_label = QLabel("5.0 Hz")
        self.rate_label.setFont(QFont(MONO_FONT, FONT_SIZES['tiny']))
        self.rate_label.setAlignment(Qt.AlignCenter)
        self.rate_label.setStyleSheet(f"color: {COLORS['text']};")
        right_col.addWidget(self.rate_label)
        
        layout.addLayout(right_col)
        
        self.setStyleSheet(f"""
            LFOWidget {{
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                background-color: {COLORS['background']};
            }}
        """)
        
    def set_wip_mode(self, enabled=True):
        """Apply WIP styling - grey out all controls."""
        if enabled:
            wip_btn = """
                QPushButton {
                    background-color: #1a1a1a;
                    color: #383838;
                    border: 1px solid #252525;
                }
            """
            self.wave_btn.setStyleSheet(wip_btn)
            self.sync_btn.setStyleSheet(wip_btn)
            self.clk_btn.setStyleSheet(wip_btn)
            self.rate_label.setStyleSheet("color: #383838;")
            self.findChild(QLabel, "").setStyleSheet("color: #444;") if self.findChild(QLabel) else None
            self.setStyleSheet("""
                LFOWidget {
                    border: 1px solid #252525;
                    border-radius: 4px;
                    background-color: #151515;
                }
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
    """Container for modulation sources - vertical stack for side panel."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lfos = {}
        self.setup_ui()
        
    def setup_ui(self):
        """Create modulation sources panel - vertical layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 10, 5, 10)
        layout.setSpacing(10)
        
        # Header with title and WIP badge
        header = QHBoxLayout()
        
        title = QLabel("MOD SOURCES")
        title.setFont(QFont(FONT_FAMILY, FONT_SIZES['section'], QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['text_dim']};")
        header.addWidget(title)
        
        header.addStretch()
        
        wip_badge = QLabel("COMING SOON")
        wip_badge.setStyleSheet(wip_badge_style())
        header.addWidget(wip_badge)
        
        layout.addLayout(header)
        
        # Stack LFOs vertically
        for i in range(1, 4):
            lfo = LFOWidget(i)
            lfo.setEnabled(False)  # Disable interaction
            lfo.set_wip_mode(True)  # Grey out visuals
            layout.addWidget(lfo)
            self.lfos[i] = lfo
            
        layout.addStretch()
        
    def set_master_bpm(self, bpm):
        """Update BPM for all LFOs."""
        for lfo in self.lfos.values():
            lfo.set_master_bpm(bpm)
