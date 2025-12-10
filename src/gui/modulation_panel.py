"""
Modulation Panel Component - Left frame
High-resolution sliders for expressive performance
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QSlider, QFrame, QSizePolicy, QLineEdit)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPainter, QColor


class PerformanceSlider(QSlider):
    """High-resolution slider with fine control mode."""
    
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.fine_mode = False
        self.setMinimum(0)
        self.setMaximum(10000)  # High resolution
        self.setMinimumHeight(60)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        
        # Anti-ghosting stylesheet
        self.setStyleSheet("""
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
        
        # Enable mouse wheel
        self.setFocusPolicy(Qt.StrongFocus)
        
    def mousePressEvent(self, event):
        """Track if shift is held."""
        self.fine_mode = event.modifiers() & Qt.ShiftModifier
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        """Apply fine control if shift held."""
        if self.fine_mode:
            # Get the current position and target position
            current = self.value()
            # Calculate smaller step size
            super().mouseMoveEvent(event)
            new = self.value()
            # Reduce the change by 10x for fine control
            delta = new - current
            self.setValue(current + int(delta / 10))
        else:
            super().mouseMoveEvent(event)
    
    def wheelEvent(self, event):
        """Scroll wheel for micro adjustments."""
        delta = event.angleDelta().y()
        step = 10 if delta > 0 else -10
        self.setValue(self.value() + step)
        event.accept()
        
    def mouseReleaseEvent(self, event):
        """Reset fine mode and fix ghosting."""
        self.fine_mode = False
        self.repaint()
        super().mouseReleaseEvent(event)


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
        
        # Instructions
        hint = QLabel("Shift+drag = fine control")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color: #888; font-size: 9px;")
        main_layout.addWidget(hint)
        
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
        
        # Value display (percentage)
        default_pct = int(config['default'] * 100)
        value_label = QLabel(f"{default_pct}%")
        value_label.setAlignment(Qt.AlignRight)
        value_font = QFont('Courier', 10, QFont.Bold)
        value_label.setFont(value_font)
        value_label.setStyleSheet("color: #0066cc;")
        value_label.setCursor(Qt.PointingHandCursor)
        value_label.setToolTip("Click to enter exact value")
        header.addWidget(value_label)
        
        layout.addLayout(header)
        
        # High-resolution performance slider
        slider = PerformanceSlider(Qt.Vertical)
        
        # Set default (0-10000 range)
        default_normalized = int((config['default'] - config['min']) / 
                                (config['max'] - config['min']) * 10000)
        slider.setValue(default_normalized)
        
        slider.valueChanged.connect(
            lambda val, pid=param_id, cfg=config: self.on_slider_change(pid, val, cfg)
        )
        
        layout.addWidget(slider, alignment=Qt.AlignCenter, stretch=1)
        
        # Store references
        self.sliders[param_id] = slider
        self.value_labels[param_id] = value_label
        
        return widget
        
    def on_slider_change(self, param_id, slider_value, config):
        """Handle slider change."""
        # Convert from 0-10000 to actual value
        normalized = slider_value / 10000.0
        actual_value = config['min'] + normalized * (config['max'] - config['min'])
        
        # Update display as percentage (0-100%)
        percentage = int(normalized * 100)
        self.value_labels[param_id].setText(f"{percentage}%")
        
        self.parameter_changed.emit(param_id, actual_value)
        
    def get_parameter_value(self, param_id):
        """Get current value of a parameter."""
        if param_id in self.sliders:
            slider = self.sliders[param_id]
            config = self.parameters[param_id]
            normalized = slider.value() / 10000.0
            return config['min'] + normalized * (config['max'] - config['min'])
        return None
