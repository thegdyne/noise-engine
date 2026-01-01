"""
MIDI Device Selector Widget
Dropdown for selecting MIDI input device, auto-refreshes on open
"""

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QComboBox
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFont
import json
import os

from .theme import COLORS, FONT_FAMILY, FONT_SIZES

# Try to import rtmidi, gracefully handle if not available
try:
    import rtmidi
    RTMIDI_AVAILABLE = True
except ImportError:
    RTMIDI_AVAILABLE = False
    # Late import to avoid circular dependency
    def _log_rtmidi_warning():
        try:
            from src.utils.logger import logger
            logger.warning("python-rtmidi not available, MIDI device selection disabled", component="MIDI")
        except ImportError:
            pass
    _log_rtmidi_warning()


class MIDISelector(QWidget):
    """Dropdown for selecting MIDI input device."""
    
    device_changed = pyqtSignal(str)  # Emits device name (or empty string for None)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_device = ""
        self._config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'midi_config.json')
        self.midi_in = None
        
        if RTMIDI_AVAILABLE:
            self.midi_in = rtmidi.MidiIn()
        
        self.setup_ui()
        
    def setup_ui(self):
        """Create the selector UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        label = QLabel("MIDI:")
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
        
        # Override showPopup to refresh on open
        original_show_popup = self.combo.showPopup
        def refresh_and_show():
            self.refresh_devices()
            original_show_popup()
        self.combo.showPopup = refresh_and_show
        
        layout.addWidget(self.combo)
        
        # Initial population
        self.refresh_devices()

    def refresh_devices(self):
        """Refresh the list of available MIDI devices."""
        current_text = self.combo.currentText()

        # If no current selection, try loading last used device
        if not current_text or current_text == "None":
            current_text = self._load_last_device()

        self.combo.blockSignals(True)
        self.combo.clear()
        self.combo.addItem("None")

        if RTMIDI_AVAILABLE and self.midi_in:
            ports = self.midi_in.get_ports()
            for port in ports:
                # Clean up port name (remove index suffix if present)
                clean_name = port
                self.combo.addItem(clean_name)

            # Try to restore previous selection
            index = self.combo.findText(current_text)
            if index >= 0:
                self.combo.setCurrentIndex(index)
                # Emit signal to actually connect
                if current_text and current_text != "None":
                    self.current_device = current_text
                    self.device_changed.emit(current_text)
            else:
                self.combo.setCurrentIndex(0)

        self.combo.blockSignals(False)

    def on_device_selected(self, index):
        """Handle device selection."""
        device_name = self.combo.currentText()
        
        if device_name == "None":
            self.current_device = ""
            self.device_changed.emit("")
        else:
            self.current_device = device_name
            self.device_changed.emit(device_name)
            self._save_last_device(device_name)
            
    def get_current_device(self):
        """Get currently selected device name."""
        return self.current_device
    
    def get_port_index(self, device_name):
        """Get the rtmidi port index for a device name."""
        if not RTMIDI_AVAILABLE or not self.midi_in:
            return -1
            
        ports = self.midi_in.get_ports()
        for i, port in enumerate(ports):
            if port == device_name:
                return i
        return -1

    def _save_last_device(self, device_name):
        """Save last selected device to config."""
        try:
            with open(self._config_path, 'w') as f:
                json.dump({'last_device': device_name}, f)
        except (IOError, OSError) as e:
            # Non-critical: config save failure doesn't affect functionality
            pass

    def _load_last_device(self):
        """Load last selected device from config."""
        try:
            if os.path.exists(self._config_path):
                with open(self._config_path, 'r') as f:
                    data = json.load(f)
                    return data.get('last_device', '')
        except (IOError, OSError, json.JSONDecodeError):
            # Non-critical: missing/corrupt config just means no device pre-selected
            pass
        return ''