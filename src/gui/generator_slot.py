"""
Generator Slot Component
Individual generator with base parameters
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QSlider, QPushButton, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from .theme import COLORS, button_style, slider_style


class MiniSlider(QSlider):
    """Compact vertical slider for generator params."""
    
    def __init__(self, parent=None):
        super().__init__(Qt.Vertical, parent)
        self.setMinimum(0)
        self.setMaximum(1000)
        self.setValue(500)
        self.setFixedWidth(25)
        self.setMinimumHeight(50)
        self.setStyleSheet(slider_style())


class GeneratorSlot(QWidget):
    """A single generator slot with base parameters."""
    
    clicked = pyqtSignal(int)
    parameter_changed = pyqtSignal(int, str, float)
    filter_type_changed = pyqtSignal(int, str)
    clock_enabled_changed = pyqtSignal(int, bool)
    clock_rate_changed = pyqtSignal(int, str)
    
    def __init__(self, slot_id, generator_type="Empty", parent=None):
        super().__init__(parent)
        self.slot_id = slot_id
        self.generator_type = generator_type
        self.active = False
        self.filter_type = "LP"
        self.clock_enabled = False
        self.clock_rate = "CLK"
        
        self.setMinimumSize(200, 200)
        self.setup_ui()
        self.update_style()
        
    def setup_ui(self):
        """Create slot interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(5)
        
        header = QHBoxLayout()
        
        self.id_label = QLabel(f"GEN {self.slot_id}")
        self.id_label.setFont(QFont('Helvetica', 9))
        self.id_label.setStyleSheet(f"color: {COLORS['text']};")
        header.addWidget(self.id_label)
        
        header.addStretch()
        
        self.type_label = QLabel(self.generator_type)
        self.type_label.setFont(QFont('Helvetica', 11, QFont.Bold))
        self.type_label.setAlignment(Qt.AlignRight)
        self.type_label.setCursor(Qt.PointingHandCursor)
        header.addWidget(self.type_label)
        
        layout.addLayout(header)
        
        params_frame = QFrame()
        params_frame.setStyleSheet(f"background-color: {COLORS['background']}; border-radius: 4px;")
        params_layout = QHBoxLayout(params_frame)
        params_layout.setContentsMargins(8, 8, 8, 8)
        params_layout.setSpacing(5)
        
        params = [
            ('FRQ', 'frequency', 'Frequency / Rate'),
            ('CUT', 'cutoff', 'Filter Cutoff'),
            ('RES', 'resonance', 'Filter Resonance'),
            ('ATK', 'attack', 'VCA Attack'),
            ('DEC', 'decay', 'VCA Decay'),
        ]
        
        self.sliders = {}
        
        for label, key, tooltip in params:
            param_widget = QWidget()
            param_layout = QVBoxLayout(param_widget)
            param_layout.setContentsMargins(0, 0, 0, 0)
            param_layout.setSpacing(2)
            
            param_layout.addStretch()
            
            lbl = QLabel(label)
            lbl.setFont(QFont('Courier', 8, QFont.Bold))
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"color: {COLORS['text']};")
            param_layout.addWidget(lbl)
            
            slider = MiniSlider()
            slider.setToolTip(tooltip)
            slider.valueChanged.connect(
                lambda v, k=key: self.on_param_changed(k, v / 1000.0)
            )
            slider.setEnabled(False)
            param_layout.addWidget(slider, alignment=Qt.AlignCenter)
            
            self.sliders[key] = slider
            params_layout.addWidget(param_widget)
        
        # Spacer between sliders and buttons
        params_layout.addSpacing(5)
        
        # Buttons column
        buttons_widget = QWidget()
        buttons_widget.setFixedWidth(38)
        buttons_layout = QVBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(3)
        
        # Filter type button
        self.filter_btn = QPushButton("LP")
        self.filter_btn.setFixedSize(36, 24)
        self.filter_btn.setFont(QFont('Courier', 9, QFont.Bold))
        self.filter_btn.setStyleSheet(button_style('enabled'))
        self.filter_btn.clicked.connect(self.cycle_filter_type)
        self.filter_btn.setEnabled(False)
        self.filter_btn.setToolTip("Filter Type: LP / HP / BP")
        buttons_layout.addWidget(self.filter_btn)
        
        # ENV toggle
        self.clock_toggle = QPushButton("ENV")
        self.clock_toggle.setFixedSize(36, 24)
        self.clock_toggle.setFont(QFont('Courier', 8, QFont.Bold))
        self.clock_toggle.setStyleSheet(button_style('disabled'))
        self.clock_toggle.clicked.connect(self.toggle_clock)
        self.clock_toggle.setEnabled(False)
        self.clock_toggle.setToolTip("Envelope ON/OFF (OFF = drone)")
        buttons_layout.addWidget(self.clock_toggle)
        
        # CLK rate button
        self.rate_btn = QPushButton("CLK")
        self.rate_btn.setFixedSize(36, 24)
        self.rate_btn.setFont(QFont('Courier', 8))
        self.rate_btn.setStyleSheet(button_style('inactive'))
        self.rate_btn.clicked.connect(self.cycle_clock_rate)
        self.rate_btn.setEnabled(False)
        self.rate_btn.setToolTip("Clock division")
        buttons_layout.addWidget(self.rate_btn)
        
        buttons_layout.addStretch()
        params_layout.addWidget(buttons_widget)
        
        layout.addWidget(params_frame)
        
        # Status
        status_layout = QHBoxLayout()
        status_layout.setSpacing(15)
        
        self.audio_indicator = QLabel("🔇 Audio")
        self.audio_indicator.setFont(QFont('Helvetica', 9))
        self.audio_indicator.setStyleSheet(f"color: {COLORS['audio_off']};")
        status_layout.addWidget(self.audio_indicator)
        
        self.midi_indicator = QLabel("🎹 MIDI")
        self.midi_indicator.setFont(QFont('Helvetica', 9))
        self.midi_indicator.setStyleSheet(f"color: {COLORS['midi_off']};")
        status_layout.addWidget(self.midi_indicator)
        
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
    def update_style(self):
        """Update appearance based on state."""
        if self.generator_type == "Empty":
            border_color = COLORS['border']
            bg_color = COLORS['background']
        elif self.active:
            border_color = COLORS['border_active']
            bg_color = '#1a2a1a'
        else:
            border_color = COLORS['border_light']
            bg_color = COLORS['background_light']
            
        self.setStyleSheet(f"""
            GeneratorSlot {{
                border: 2px solid {border_color};
                border-radius: 6px;
                background-color: {bg_color};
            }}
        """)
        
    def update_clock_style(self):
        """Update clock button styles based on state."""
        if self.clock_enabled:
            # ENV enabled - GREEN
            self.clock_toggle.setStyleSheet(button_style('enabled'))
            # CLK rate - ORANGE (submenu active)
            self.rate_btn.setEnabled(True and self.generator_type != "Empty")
            self.rate_btn.setStyleSheet(button_style('submenu'))
        else:
            # ENV disabled
            self.clock_toggle.setStyleSheet(button_style('disabled'))
            # CLK rate inactive
            self.rate_btn.setEnabled(False)
            self.rate_btn.setStyleSheet(button_style('inactive'))
        
    def set_generator_type(self, gen_type):
        """Change generator type."""
        self.generator_type = gen_type
        self.type_label.setText(gen_type)
        
        enabled = gen_type != "Empty"
        for slider in self.sliders.values():
            slider.setEnabled(enabled)
        self.filter_btn.setEnabled(enabled)
        self.clock_toggle.setEnabled(enabled)
        self.update_clock_style()
        
        self.update_style()
        
    def set_active(self, active):
        """Set active state."""
        self.active = active
        self.update_style()
        
    def set_audio_status(self, active):
        """Update audio indicator."""
        if active:
            self.audio_indicator.setText("🔊 Audio")
            self.audio_indicator.setStyleSheet(f"color: {COLORS['audio_on']};")
        else:
            self.audio_indicator.setText("🔇 Audio")
            self.audio_indicator.setStyleSheet(f"color: {COLORS['audio_off']};")
            
    def set_midi_status(self, active):
        """Update MIDI indicator."""
        if active:
            self.midi_indicator.setText("🎹 MIDI")
            self.midi_indicator.setStyleSheet(f"color: {COLORS['midi_on']};")
        else:
            self.midi_indicator.setText("🎹 MIDI")
            self.midi_indicator.setStyleSheet(f"color: {COLORS['midi_off']};")
            
    def cycle_filter_type(self):
        """Cycle through filter types."""
        types = ["LP", "HP", "BP"]
        idx = types.index(self.filter_type)
        self.filter_type = types[(idx + 1) % len(types)]
        self.filter_btn.setText(self.filter_type)
        self.filter_type_changed.emit(self.slot_id, self.filter_type)
        print(f"Gen {self.slot_id} filter: {self.filter_type}")
        
    def toggle_clock(self):
        """Toggle envelope ON/OFF."""
        self.clock_enabled = not self.clock_enabled
        self.update_clock_style()
        self.clock_enabled_changed.emit(self.slot_id, self.clock_enabled)
        state = "ON" if self.clock_enabled else "OFF"
        print(f"Gen {self.slot_id} ENV: {state}")
        
    def cycle_clock_rate(self):
        """Cycle through clock divisions."""
        rates = ["CLK", "/2", "/4", "/8", "/16"]
        idx = rates.index(self.clock_rate)
        self.clock_rate = rates[(idx + 1) % len(rates)]
        self.rate_btn.setText(self.clock_rate)
        self.clock_rate_changed.emit(self.slot_id, self.clock_rate)
        print(f"Gen {self.slot_id} CLK: {self.clock_rate}")
        
    def on_param_changed(self, param_name, value):
        """Handle parameter change."""
        self.parameter_changed.emit(self.slot_id, param_name, value)
        
    def mousePressEvent(self, event):
        """Handle click to change generator type."""
        if event.button() == Qt.LeftButton:
            if event.pos().y() < 30:
                self.clicked.emit(self.slot_id)
