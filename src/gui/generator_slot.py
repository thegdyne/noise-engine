"""
Generator Slot Component
Individual generator in the grid - responsive sizing
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QSizePolicy
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont


class GeneratorSlot(QWidget):
    """A single generator slot in the grid."""
    
    # Signals
    clicked = pyqtSignal(int)  # Emits slot ID when clicked
    
    def __init__(self, slot_id, generator_type="Empty", parent=None):
        super().__init__(parent)
        self.slot_id = slot_id
        self.generator_type = generator_type
        self.active = False
        
        # Responsive sizing instead of fixed
        self.setMinimumSize(120, 100)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        self.setup_ui()
        
        # Make clickable
        self.setMouseTracking(True)
        
    def setup_ui(self):
        """Create slot interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Slot number
        self.id_label = QLabel(f"GEN {self.slot_id}")
        id_font = QFont('Helvetica', 9, QFont.Bold)
        self.id_label.setFont(id_font)
        self.id_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.id_label)
        
        # Generator type
        self.type_label = QLabel(self.generator_type)
        type_font = QFont('Helvetica', 11, QFont.Bold)
        self.type_label.setFont(type_font)
        self.type_label.setAlignment(Qt.AlignCenter)
        self.type_label.setWordWrap(True)
        layout.addWidget(self.type_label)
        
        layout.addStretch()
        
        # Status indicators
        status_layout = QVBoxLayout()
        
        self.audio_indicator = QLabel("🔊 Audio")
        self.audio_indicator.setAlignment(Qt.AlignCenter)
        self.audio_indicator.setStyleSheet("color: gray;")
        status_layout.addWidget(self.audio_indicator)
        
        self.midi_indicator = QLabel("📡 MIDI")
        self.midi_indicator.setAlignment(Qt.AlignCenter)
        self.midi_indicator.setStyleSheet("color: gray;")
        status_layout.addWidget(self.midi_indicator)
        
        layout.addLayout(status_layout)
        
        # Style the slot
        self.update_style()
        
    def update_style(self):
        """Update slot appearance based on state."""
        if self.generator_type == "Empty":
            border_color = "#666"
            bg_color = "#2a2a2a"
        elif self.active:
            border_color = "#44ff44"
            bg_color = "#1a3a1a"
        else:
            border_color = "#888"
            bg_color = "#3a3a3a"
            
        self.setStyleSheet(f"""
            GeneratorSlot {{
                border: 2px solid {border_color};
                border-radius: 5px;
                background-color: {bg_color};
            }}
            GeneratorSlot:hover {{
                border-color: #aaaaaa;
            }}
        """)
        
    def set_generator_type(self, gen_type):
        """Change generator type."""
        self.generator_type = gen_type
        self.type_label.setText(gen_type)
        self.update_style()
        
    def set_active(self, active):
        """Set active state."""
        self.active = active
        self.update_style()
        
        if active:
            self.audio_indicator.setStyleSheet("color: #44ff44;")
        else:
            self.audio_indicator.setStyleSheet("color: gray;")
            
    def set_audio_status(self, enabled):
        """Set audio output status."""
        if enabled:
            self.audio_indicator.setStyleSheet("color: #44ff44;")
            self.audio_indicator.setText("🔊 Audio")
        else:
            self.audio_indicator.setStyleSheet("color: gray;")
            self.audio_indicator.setText("🔊 ━")
            
    def set_midi_status(self, enabled):
        """Set MIDI output status."""
        if enabled:
            self.midi_indicator.setStyleSheet("color: #4444ff;")
            self.midi_indicator.setText("📡 MIDI")
        else:
            self.midi_indicator.setStyleSheet("color: gray;")
            self.midi_indicator.setText("📡 ━")
            
    def mousePressEvent(self, event):
        """Handle click."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.slot_id)
