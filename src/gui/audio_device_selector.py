"""
Audio Device Selector Widget
Dropdown for selecting audio output device, queries SuperCollider
"""

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QComboBox
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFont

from .theme import COLORS, FONT_FAMILY, FONT_SIZES


class AudioDeviceSelector(QWidget):
    """Dropdown for selecting audio output device."""
    
    device_changed = pyqtSignal(str)  # Emits device name
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_device = ""
        self.devices = []
        self.setup_ui()
        
    def setup_ui(self):
        """Create the selector UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        label = QLabel("Audio:")
        label.setFont(QFont(FONT_FAMILY, FONT_SIZES['small']))
        label.setStyleSheet(f"color: {COLORS['text']};")
        layout.addWidget(label)
        
        self.combo = QComboBox()
        self.combo.setMinimumWidth(150)
        self.combo.setFont(QFont(FONT_FAMILY, FONT_SIZES['small']))
        self.combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['background']};
                color: {COLORS['text_bright']};
                border: 1px solid {COLORS['border']};
                border-radius: 3px;
                padding: 3px 8px;
            }}
            QComboBox:hover {{
                border-color: {COLORS['border_light']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid {COLORS['text']};
                margin-right: 5px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['background']};
                color: {COLORS['text_bright']};
                selection-background-color: {COLORS['enabled']};
                selection-color: {COLORS['enabled_text']};
                border: 1px solid {COLORS['border']};
            }}
        """)
        
        # Connect signals
        self.combo.activated.connect(self.on_device_selected)
        
        layout.addWidget(self.combo)
        
        # Start with placeholder until SC provides devices
        self.combo.addItem("(connecting...)")
        self.combo.setEnabled(False)
        
    def set_devices(self, devices, current=None):
        """Set available devices from SuperCollider.
        
        Args:
            devices: List of device name strings
            current: Currently active device name (optional)
        """
        self.devices = devices
        
        self.combo.blockSignals(True)
        self.combo.clear()
        
        for device in devices:
            self.combo.addItem(device)
        
        # Select current device if provided
        if current and current in devices:
            index = devices.index(current)
            self.combo.setCurrentIndex(index)
            self.current_device = current
        elif devices:
            self.combo.setCurrentIndex(0)
            self.current_device = devices[0]
        
        self.combo.setEnabled(True)
        self.combo.blockSignals(False)
        
    def on_device_selected(self, index):
        """Handle device selection."""
        device_name = self.combo.currentText()
        
        if device_name != self.current_device:
            self.current_device = device_name
            self.device_changed.emit(device_name)
            
    def get_current_device(self):
        """Get currently selected device name."""
        return self.current_device
    
    def set_enabled(self, enabled):
        """Enable/disable the selector."""
        self.combo.setEnabled(enabled)
