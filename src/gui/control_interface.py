"""
GUI control interface for the noise engine.
Vertical sliders for better control feel.
"""

import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QSlider, QPushButton)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.config.parameters import PARAMETERS
from src.audio.osc_bridge import OSCBridge


class ControlInterface(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Noise Engine - Control Interface")
        self.setGeometry(100, 100, 700, 500)
        
        # OSC Bridge
        self.osc = OSCBridge()
        self.osc_connected = False
        
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
        
        # Connection button
        self.connect_button = QPushButton("Connect to SuperCollider")
        self.connect_button.clicked.connect(self.toggle_connection)
        main_layout.addWidget(self.connect_button)
        
        # Sliders container - HORIZONTAL layout for vertical sliders
        sliders_layout = QHBoxLayout()
        sliders_layout.setSpacing(30)
        
        # Create vertical sliders for each parameter
        for param_id, param_config in PARAMETERS.items():
            self.create_parameter_slider(sliders_layout, param_id, param_config)
        
        main_layout.addLayout(sliders_layout)
        
        # Status label
        self.status_label = QLabel("Status: Not connected")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)
        
    def toggle_connection(self):
        """Connect or disconnect from SuperCollider."""
        if not self.osc_connected:
            # Try to connect
            if self.osc.connect():
                self.osc_connected = True
                self.connect_button.setText("Disconnect")
                self.status_label.setText("Status: Connected ✓")
                self.status_label.setStyleSheet("color: green; font-weight: bold;")
                
                # Send initial values
                self.osc.send_all_parameters(self.param_values)
                print("✓ Initial parameters sent to SuperCollider")
            else:
                self.status_label.setText("Status: Connection Failed - Is SuperCollider running?")
                self.status_label.setStyleSheet("color: red; font-weight: bold;")
        else:
            # Disconnect
            self.osc_connected = False
            self.connect_button.setText("Connect to SuperCollider")
            self.status_label.setText("Status: Disconnected")
            self.status_label.setStyleSheet("color: orange; font-weight: bold;")
        
    def create_parameter_slider(self, parent_layout, param_id, config):
        """Create a vertical slider for a parameter."""
        # Container for this parameter (vertical layout)
        param_layout = QVBoxLayout()
        param_layout.setSpacing(10)
        param_layout.setAlignment(Qt.AlignCenter)
        
        # Parameter name at top
        name_label = QLabel(config['name'])
        name_font = QFont('Helvetica', 11, QFont.Bold)
        name_label.setFont(name_font)
        name_label.setAlignment(Qt.AlignCenter)
        param_layout.addWidget(name_label)
        
        # Value display
        value_label = QLabel(f"{config['default']:.2f}")
        value_font = QFont('Menlo', 12, QFont.Bold)
        value_label.setFont(value_font)
        value_label.setStyleSheet("color: #0066cc;")
        value_label.setAlignment(Qt.AlignCenter)
        param_layout.addWidget(value_label)
        
        # VERTICAL Slider
        slider = QSlider(Qt.Vertical)  # Changed to Vertical!
        slider.setMinimum(0)
        slider.setMaximum(1000)
        slider.setFixedHeight(250)  # Taller slider
        
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
        
        # Set default value (inverted for vertical - 0 at bottom)
        default_normalized = int((config['default'] - config['min']) / 
                                (config['max'] - config['min']) * 1000)
        slider.setValue(default_normalized)
        
        # Connect slider to handler
        slider.valueChanged.connect(
            lambda value, pid=param_id, cfg=config: self.on_slider_change(pid, value, cfg)
        )
        
        # Force repaint on slider release
        slider.sliderReleased.connect(lambda s=slider: s.repaint())
        
        param_layout.addWidget(slider, alignment=Qt.AlignCenter)
        
        # Add to parent layout
        parent_layout.addLayout(param_layout)
        
        # Store references
        self.sliders[param_id] = slider
        self.value_labels[param_id] = value_label
        self.param_values[param_id] = config['default']
        
    def on_slider_change(self, param_id, slider_value, config):
        """Handle slider value changes."""
        # Convert slider value to parameter range
        normalized = slider_value / 1000.0
        actual_value = config['min'] + normalized * (config['max'] - config['min'])
        
        # Update stored value
        self.param_values[param_id] = actual_value
        
        # Update display label
        self.value_labels[param_id].setText(f"{actual_value:.2f}")
        
        # Send via OSC if connected
        if self.osc_connected:
            self.osc.send_parameter(param_id, actual_value)
        
        # Print to console
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
    print("1. Start SuperCollider and run init.scd")
    print("2. Click 'Connect to SuperCollider'")
    print("3. Move sliders to control sound")
    print("=" * 50)
    
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    window = ControlInterface()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
