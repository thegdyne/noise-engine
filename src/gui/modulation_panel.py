"""
Modulation Panel Component
Global modulation parameters
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from .theme import COLORS, MONO_FONT
from .widgets import DragSlider


class ModulationPanel(QWidget):
    """Panel for global modulation parameters."""
    
    parameter_changed = pyqtSignal(str, float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parameters = {}
        self.setup_ui()
        
    def setup_ui(self):
        """Create the panel."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        title = QLabel("MODULATION")
        title_font = QFont('Helvetica', 12, QFont.Bold)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {COLORS['text_bright']};")
        layout.addWidget(title)
        
        # Parameters in horizontal row with vertical sliders
        params_frame = QFrame()
        params_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['background']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
            }}
        """)
        
        params_layout = QHBoxLayout(params_frame)
        params_layout.setContentsMargins(10, 10, 10, 10)
        params_layout.setSpacing(15)
        
        params = [
            ('gravity', 'GRV', 'Gravity', 0.5),
            ('density', 'DNS', 'Density', 0.5),
            ('filter_cutoff', 'FLT', 'Filter', 0.7),
            ('amplitude', 'AMP', 'Amplitude', 0.5),
        ]
        
        for param_id, short_label, tooltip, default in params:
            param_widget = self.create_parameter(param_id, short_label, tooltip, default)
            params_layout.addWidget(param_widget)
            
        layout.addWidget(params_frame)
        layout.addStretch()
        
    def create_parameter(self, param_id, label, tooltip, default):
        """Create a vertical parameter control."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        
        # Label at top
        lbl = QLabel(label)
        lbl.setFont(QFont(MONO_FONT, 9, QFont.Bold))
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(f"color: {COLORS['text_bright']};")
        lbl.setToolTip(tooltip)
        layout.addWidget(lbl)
        
        # Vertical slider
        slider = DragSlider()
        slider.setMinimumHeight(80)
        slider.setValue(int(default * 1000))
        slider.setToolTip(tooltip)
        slider.valueChanged.connect(
            lambda v, pid=param_id: self.on_value_changed(pid, v / 1000.0)
        )
        layout.addWidget(slider, alignment=Qt.AlignCenter)
        
        # Value label at bottom
        value_lbl = QLabel(f"{default:.2f}")
        value_lbl.setFont(QFont(MONO_FONT, 8))
        value_lbl.setAlignment(Qt.AlignCenter)
        value_lbl.setStyleSheet(f"color: {COLORS['text']};")
        layout.addWidget(value_lbl)
        
        self.parameters[param_id] = {
            'slider': slider,
            'value_label': value_lbl,
            'value': default
        }
        
        return widget
        
    def on_value_changed(self, param_id, value):
        """Handle parameter value change."""
        if param_id in self.parameters:
            self.parameters[param_id]['value'] = value
            self.parameters[param_id]['value_label'].setText(f"{value:.2f}")
            self.parameter_changed.emit(param_id, value)
            
    def get_parameter_value(self, param_id):
        """Get current value of a parameter."""
        if param_id in self.parameters:
            return self.parameters[param_id]['value']
        return None
