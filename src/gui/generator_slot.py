"""
Generator Slot Component
Individual generator with base parameters
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QSlider, QPushButton, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont


class MiniSlider(QSlider):
    """Compact vertical slider for generator params."""
    
    def __init__(self, parent=None):
        super().__init__(Qt.Vertical, parent)
        self.setMinimum(0)
        self.setMaximum(1000)
        self.setValue(500)
        self.setFixedWidth(25)
        self.setMinimumHeight(50)
        
        self.setStyleSheet("""
            QSlider::groove:vertical {
                border: 1px solid #555;
                width: 8px;
                background: #333;
                border-radius: 4px;
            }
            QSlider::handle:vertical {
                background: #888;
                border: 1px solid #666;
                height: 12px;
                margin: 0 -3px;
                border-radius: 6px;
            }
            QSlider::handle:vertical:hover {
                background: #aaa;
            }
        """)
        
    def set_normalized(self, value):
        """Set value 0.0-1.0"""
        self.setValue(int(value * 1000))
        
    def get_normalized(self):
        """Get value 0.0-1.0"""
        return self.value() / 1000.0


class GeneratorSlot(QWidget):
    """A single generator slot with base parameters."""
    
    clicked = pyqtSignal(int)
    parameter_changed = pyqtSignal(int, str, float)
    filter_type_changed = pyqtSignal(int, str)
    vca_clock_changed = pyqtSignal(int, str)
    
    def __init__(self, slot_id, generator_type="Empty", parent=None):
        super().__init__(parent)
        self.slot_id = slot_id
        self.generator_type = generator_type
        self.active = False
        self.filter_type = "LP"
        self.vca_clock = "Off"
        
        self.setMinimumSize(180, 200)
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
        self.id_label.setStyleSheet("color: #888;")
        header.addWidget(self.id_label)
        
        header.addStretch()
        
        self.type_label = QLabel(self.generator_type)
        self.type_label.setFont(QFont('Helvetica', 11, QFont.Bold))
        self.type_label.setAlignment(Qt.AlignRight)
        self.type_label.setCursor(Qt.PointingHandCursor)
        header.addWidget(self.type_label)
        
        layout.addLayout(header)
        
        params_frame = QFrame()
        params_frame.setStyleSheet("background-color: #1a1a1a; border-radius: 4px;")
        params_layout = QHBoxLayout(params_frame)
        params_layout.setContentsMargins(8, 8, 8, 8)
        params_layout.setSpacing(5)
        
        params = [
            ('FRQ', 'frequency', 'Frequency / Pitch'),
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
            
            # Stretch to push content to bottom
            param_layout.addStretch()
            
            # Label just above slider
            lbl = QLabel(label)
            lbl.setFont(QFont('Courier', 8, QFont.Bold))
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #888;")
            param_layout.addWidget(lbl)
            
            # Slider below label
            slider = MiniSlider()
            slider.setToolTip(tooltip)
            slider.valueChanged.connect(
                lambda v, k=key: self.on_param_changed(k, v / 1000.0)
            )
            slider.setEnabled(False)
            param_layout.addWidget(slider, alignment=Qt.AlignCenter)
            
            self.sliders[key] = slider
            params_layout.addWidget(param_widget)
        
        buttons_widget = QWidget()
        buttons_layout = QVBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(5, 0, 0, 0)
        buttons_layout.setSpacing(5)
        
        self.filter_btn = QPushButton("LP")
        self.filter_btn.setFixedSize(32, 24)
        self.filter_btn.setFont(QFont('Courier', 9, QFont.Bold))
        self.filter_btn.setStyleSheet("""
            QPushButton {
                background-color: #335533;
                color: #88ff88;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #446644;
            }
            QPushButton:disabled {
                background-color: #222;
                color: #444;
            }
        """)
        self.filter_btn.clicked.connect(self.cycle_filter_type)
        self.filter_btn.setEnabled(False)
        self.filter_btn.setToolTip("Filter Type: LP / HP / BP")
        buttons_layout.addWidget(self.filter_btn)
        
        self.clock_btn = QPushButton("CLK")
        self.clock_btn.setFixedSize(32, 24)
        self.clock_btn.setFont(QFont('Courier', 8))
        self.clock_btn.setStyleSheet("""
            QPushButton {
                background-color: #333;
                color: #888;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #444;
            }
            QPushButton:disabled {
                background-color: #222;
                color: #444;
            }
        """)
        self.clock_btn.clicked.connect(self.cycle_vca_clock)
        self.clock_btn.setEnabled(False)
        self.clock_btn.setToolTip("VCA Clock Sync")
        buttons_layout.addWidget(self.clock_btn)
        
        buttons_layout.addStretch()
        params_layout.addWidget(buttons_widget)
        
        layout.addWidget(params_frame)
        
        status_layout = QHBoxLayout()
        status_layout.setSpacing(15)
        
        self.audio_indicator = QLabel("🔇 Audio")
        self.audio_indicator.setFont(QFont('Helvetica', 9))
        self.audio_indicator.setStyleSheet("color: #555;")
        status_layout.addWidget(self.audio_indicator)
        
        self.midi_indicator = QLabel("🎹 MIDI")
        self.midi_indicator.setFont(QFont('Helvetica', 9))
        self.midi_indicator.setStyleSheet("color: #555;")
        status_layout.addWidget(self.midi_indicator)
        
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
    def update_style(self):
        """Update appearance based on state."""
        if self.generator_type == "Empty":
            border_color = "#333"
            bg_color = "#1a1a1a"
        elif self.active:
            border_color = "#44aa44"
            bg_color = "#1a2a1a"
        else:
            border_color = "#555"
            bg_color = "#222"
            
        self.setStyleSheet(f"""
            GeneratorSlot {{
                border: 2px solid {border_color};
                border-radius: 6px;
                background-color: {bg_color};
            }}
        """)
        
    def set_generator_type(self, gen_type):
        """Change generator type."""
        self.generator_type = gen_type
        self.type_label.setText(gen_type)
        
        enabled = gen_type != "Empty"
        for slider in self.sliders.values():
            slider.setEnabled(enabled)
        self.filter_btn.setEnabled(enabled)
        self.clock_btn.setEnabled(enabled)
        
        self.update_style()
        
    def set_active(self, active):
        """Set active state."""
        self.active = active
        self.update_style()
        
    def set_audio_status(self, active):
        """Update audio indicator."""
        if active:
            self.audio_indicator.setText("🔊 Audio")
            self.audio_indicator.setStyleSheet("color: #44ff44;")
        else:
            self.audio_indicator.setText("🔇 Audio")
            self.audio_indicator.setStyleSheet("color: #555;")
            
    def set_midi_status(self, active):
        """Update MIDI indicator."""
        if active:
            self.midi_indicator.setText("🎹 MIDI")
            self.midi_indicator.setStyleSheet("color: #ffaa00;")
        else:
            self.midi_indicator.setText("🎹 MIDI")
            self.midi_indicator.setStyleSheet("color: #555;")
            
    def cycle_filter_type(self):
        """Cycle through filter types."""
        types = ["LP", "HP", "BP"]
        idx = types.index(self.filter_type)
        self.filter_type = types[(idx + 1) % len(types)]
        self.filter_btn.setText(self.filter_type)
        self.filter_type_changed.emit(self.slot_id, self.filter_type)
        print(f"Gen {self.slot_id} filter: {self.filter_type}")
        
    def cycle_vca_clock(self):
        """Cycle through VCA clock options."""
        options = ["Off", "CLK", "/2", "/4", "/8", "/16"]
        idx = options.index(self.vca_clock)
        self.vca_clock = options[(idx + 1) % len(options)]
        self.clock_btn.setText(self.vca_clock if self.vca_clock != "Off" else "CLK")
        
        if self.vca_clock != "Off":
            self.clock_btn.setStyleSheet("""
                QPushButton {
                    background-color: #335533;
                    color: #88ff88;
                    border-radius: 3px;
                }
            """)
        else:
            self.clock_btn.setStyleSheet("""
                QPushButton {
                    background-color: #333;
                    color: #888;
                    border-radius: 3px;
                }
            """)
        
        self.vca_clock_changed.emit(self.slot_id, self.vca_clock)
        print(f"Gen {self.slot_id} VCA clock: {self.vca_clock}")
        
    def on_param_changed(self, param_name, value):
        """Handle parameter change."""
        self.parameter_changed.emit(self.slot_id, param_name, value)
        
    def mousePressEvent(self, event):
        """Handle click to change generator type."""
        if event.button() == Qt.LeftButton:
            if event.pos().y() < 30:
                self.clicked.emit(self.slot_id)
