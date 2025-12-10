"""
Modulation Panel Component - Left frame
Physics-based parameter controls
Responsive sizing with ghosting fix
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QSlider, QFrame, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont


class ModulationPanel(QWidget):
    """Panel with modulation parameter sliders."""
    
    # Signals
    parameter_changed = pyqtSignal(str, float)  # (param_name, value)
    
    def __init__(self, parameters=None, parent=None):
        super().__init__(parent)
        
        # Default parameters if none provided
        if parameters is None:
            from src.config.parameters import PARAMETERS
            self.parameters = PARAMETERS
        else:
            self.parameters = parameters
            
        self.sliders = {}
        self.value_labels = {}
        
        # Responsive sizing
        self.setMinimumWidth(150)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        
        self.setup_ui()
        
    def setup_ui(self):
        """Create the modulation interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)
        
        # Title
        title = QLabel("MODULATION")
        title_font = QFont('Helvetica', 12, QFont.Bold)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        main_layout.addWidget(separator)
        
        # Create sliders for each parameter
        for param_id, param_config in self.parameters.items():
            param_widget = self.create_parameter_control(param_id, param_config)
            main_layout.addWidget(param_widget)
            
        main_layout.addStretch()
        
    def create_parameter_control(self, param_id, config):
        """Create a single parameter control."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(5)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header with name and value
        header = QHBoxLayout()
        
        # Parameter name
        name_label = QLabel(config['name'])
        name_font = QFont('Helvetica', 10, QFont.Bold)
        name_label.setFont(name_font)
        header.addWidget(name_label)
        
        header.addStretch()
        
        # Value display
        value_label = QLabel(f"{config['default']:.2f}")
        value_font = QFont('Courier', 10)
        value_label.setFont(value_font)
        value_label.setStyleSheet("color: #0066cc;")
        header.addWidget(value_label)
        
        layout.addLayout(header)
        
        # Slider with anti-ghosting stylesheet
        slider = QSlider(Qt.Vertical)
        slider.setMinimum(0)
        slider.setMaximum(1000)
        slider.setMinimumHeight(60)
        slider.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        
        # Anti-ghosting stylesheet
        slider.setStyleSheet("""
            QSlider::groove:vertical {
                border: 1px solid #999999;
                width: 10px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #B1B1B1, stop:1 #c4c4c4);
                margin: 0 2px;
                border-radius: 5px;
            }
            QSlider::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #d4d4d4, stop:1 #8f8f8f);
                border: 1px solid #5c5c5c;
                height: 20px;
                margin: 0 -5px;
                border-radius: 10px;
            }
            QSlider::handle:vertical:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #f4f4f4, stop:1 #afafaf);
            }
        """)
        
        # Set default
        default_normalized = int((config['default'] - config['min']) / 
                                (config['max'] - config['min']) * 1000)
        slider.setValue(default_normalized)
        
        slider.valueChanged.connect(
            lambda val, pid=param_id, cfg=config: self.on_slider_change(pid, val, cfg)
        )
        
        # Force repaint on release - fixes ghosting
        slider.sliderReleased.connect(lambda s=slider: s.repaint())
        
        layout.addWidget(slider, alignment=Qt.AlignCenter, stretch=1)
        
        # Store references
        self.sliders[param_id] = slider
        self.value_labels[param_id] = value_label
        
        return widget
        
    def on_slider_change(self, param_id, slider_value, config):
        """Handle slider change."""
        normalized = slider_value / 1000.0
        actual_value = config['min'] + normalized * (config['max'] - config['min'])
        
        self.value_labels[param_id].setText(f"{actual_value:.2f}")
        self.parameter_changed.emit(param_id, actual_value)
        
    def get_parameter_value(self, param_id):
        """Get current value of a parameter."""
        if param_id in self.sliders:
            slider = self.sliders[param_id]
            config = self.parameters[param_id]
            normalized = slider.value() / 1000.0
            return config['min'] + normalized * (config['max'] - config['min'])
        return None
