"""
Audio Device Display Widget
Shows current audio output device (display only)
"""

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFont

from .theme import COLORS, FONT_FAMILY, FONT_SIZES


class AudioDeviceSelector(QWidget):
    """Display for current audio output device (read-only)."""
    
    device_changed = pyqtSignal(str)  # Kept for API compatibility, never emitted
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_device = ""
        self.setup_ui()
        
    def setup_ui(self):
        """Create the display UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        label = QLabel("Audio:")
        label.setFont(QFont(FONT_FAMILY, FONT_SIZES['small']))
        label.setStyleSheet(f"color: {COLORS['text']};")
        layout.addWidget(label)
        
        self.device_label = QLabel("(connecting...)")
        self.device_label.setFont(QFont(FONT_FAMILY, FONT_SIZES['small']))
        self.device_label.setStyleSheet(f"color: {COLORS['text_bright']};")
        layout.addWidget(self.device_label)
        
    def set_devices(self, devices, current=None):
        """Set current device display.
        
        Args:
            devices: List of device names (ignored, kept for API compatibility)
            current: Currently active device name
        """
        if current:
            self.current_device = current
            # Shorten "MacBook Pro Speakers" to "MacBook Speakers" etc
            display_name = current
            if len(display_name) > 25:
                display_name = display_name[:22] + "..."
            self.device_label.setText(display_name)
        else:
            self.device_label.setText("(default)")
            
    def get_current_device(self):
        """Get currently displayed device name."""
        return self.current_device
    
    def set_enabled(self, enabled):
        """Enable/disable - no-op for label."""
        pass
