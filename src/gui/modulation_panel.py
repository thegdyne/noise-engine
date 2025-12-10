"""
Modulation Panel Component
Global modulation parameters
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QSlider, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from .theme import COLORS, slider_style


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
        
        # Parameters
        params = [
            ('gravity', 'Gravity', 0.5),
            ('density', 'Density', 0.5),
            ('filter_cutoff', 'Filter', 0.7),
            ('amplitude', 'Amplitude', 0.5),
        ]
        
        for param_id, label, default in params:
            param_widget = self.create_parameter(param_id, label, default)
            layout.addWidget(param_widget)
            
        layout.addStretch()
        
    def create_parameter(self, param_id, label, default):
        """Create a parameter control."""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['background']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(5)
        
        # Label
        lbl = QLabel(label)
        lbl.setFont(QFont('Helvetica', 10, QFont.Bold))
        lbl.setStyleSheet(f"color: {COLORS['text_bright']}; border: none;")
        layout.addWidget(lbl)
        
        # Slider row
        slider_layout = QHBoxLayout()
        slider_layout.setSpacing(10)
        
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(0)
        slider.setMaximum(1000)
        slider.setValue(int(default * 1000))
        slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                border: 1px solid {COLORS['border_light']};
                height: 8px;
                background: {COLORS['slider_groove']};
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: {COLORS['slider_handle']};
                border: 1px solid {COLORS['border_light']};
                width: 16px;
                margin: -4px 0;
                border-radius: 8px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {COLORS['slider_handle_hover']};
            }}
        """)
        slider.valueChanged.connect(
            lambda v, pid=param_id: self.on_value_changed(pid, v / 1000.0)
        )
        slider_layout.addWidget(slider)
        
        # Value label
        value_lbl = QLabel(f"{default:.2f}")
        value_lbl.setFont(QFont('Courier', 9))
        value_lbl.setFixedWidth(40)
        value_lbl.setAlignment(Qt.AlignRight)
        value_lbl.setStyleSheet(f"color: {COLORS['text']}; border: none;")
        slider_layout.addWidget(value_lbl)
        
        layout.addLayout(slider_layout)
        
        self.parameters[param_id] = {
            'slider': slider,
            'value_label': value_lbl,
            'value': default
        }
        
        return frame
        
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
