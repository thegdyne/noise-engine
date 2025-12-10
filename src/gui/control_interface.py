"""
GUI control interface for the noise engine.
Provides sliders for parameter control using PyQt5.
"""

import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QSlider)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

# Add parent directory to path to import config
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.config.parameters import PARAMETERS


class ControlInterface(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Noise Engine - Control Interface")
        self.setGeometry(100, 100, 600, 500)
        
        # Store parameter values
        self.param_values = {}
        
        # Store slider widgets
        self.sliders = {}
        self.value_labels = {}
        
        self.setup_ui()
        
        # Force proper rendering on macOS
        self.setAttribute(Qt.WA_AcceptTouchEvents, False)
        
    def setup_ui(self):
        """Create the user interface."""
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title = QLabel("Noise Engine")
        title_font = QFont('Helvetica', 24, QFont.Bold)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel("Control Interface")
        subtitle_font = QFont('Helvetica', 14)
        subtitle.setFont(subtitle_font)
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #666;")
        main_layout.addWidget(subtitle)
        
        # Spacer
        main_layout.addSpacing(20)
        
        # Create sliders for each parameter
        for param_id, param_config in PARAMETERS.items():
            self.create_parameter_slider(main_layout, param_id, param_config)
        
        # Spacer
        main_layout.addStretch()
        
        # Status label
        self.status_label = QLabel("Status: Ready")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        main_layout.addWidget(self.status_label)
        
    def create_parameter_slider(self, layout, param_id, config):
        """Create a labeled slider for a parameter."""
        # Container for this parameter
        param_layout = QVBoxLayout()
        param_layout.setSpacing(5)
        
        # Header with label and value
        header_layout = QHBoxLayout()
        
        # Parameter name
        name_label = QLabel(config['name'])
        name_font = QFont('Helvetica', 12, QFont.Bold)
        name_label.setFont(name_font)
        header_layout.addWidget(name_label)
        
        header_layout.addStretch()
        
        # Value display
        value_label = QLabel(f"{config['default']:.3f}")
        value_font = QFont('Courier', 11)
        value_label.setFont(value_font)
        value_label.setStyleSheet("color: #0066cc;")
        header_layout.addWidget(value_label)
        
        param_layout.addLayout(header_layout)
        
        # Slider with styling to fix ghosting
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(0)
        slider.setMaximum(1000)
        
        # Style to reduce ghosting/artifacts
        slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 8px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #B1B1B1, stop:1 #c4c4c4);
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #b4b4b4, stop:1 #8f8f8f);
                border: 1px solid #5c5c5c;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #d4d4d4, stop:1 #afafaf);
            }
        """)
        
        # Set default value
        default_normalized = int((config['default'] - config['min']) / 
                                (config['max'] - config['min']) * 1000)
        slider.setValue(default_normalized)
        
        # Connect slider to handler
        slider.valueChanged.connect(
            lambda value, pid=param_id, cfg=config: self.on_slider_change(pid, value, cfg)
        )
        
        # Force repaint on slider release to clear artifacts
        slider.sliderReleased.connect(lambda s=slider: s.repaint())
        
        param_layout.addWidget(slider)
        
        # Add to main layout
        layout.addLayout(param_layout)
        
        # Store references
        self.sliders[param_id] = slider
        self.value_labels[param_id] = value_label
        self.param_values[param_id] = config['default']
        
    def on_slider_change(self, param_id, slider_value, config):
        """Handle slider value changes."""
        # Convert slider value (0-1000) to parameter range
        normalized = slider_value / 1000.0
        actual_value = config['min'] + normalized * (config['max'] - config['min'])
        
        # Update stored value
        self.param_values[param_id] = actual_value
        
        # Update display label
        self.value_labels[param_id].setText(f"{actual_value:.3f}")
        
        # Print to console (for testing)
        param_name = config['name']
        print(f"{param_name}: {actual_value:.3f}")
        
    def get_all_values(self):
        """Get current values of all parameters."""
        return self.param_values.copy()


def main():
    """Run the GUI application."""
    print("=" * 50)
    print("Noise Engine Control Interface")
    print("=" * 50)
    print("Move sliders to change parameters.")
    print("Values will be printed to console.")
    print("Close window to quit.")
    print("=" * 50)
    
    app = QApplication(sys.argv)
    
    # Enable high DPI scaling for better rendering
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    window = ControlInterface()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
