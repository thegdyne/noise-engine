"""
Crossmod Connection Popup
Popup dialog for editing crossmod connection parameters.

Shows:
- Header: "GEN X → GY PARAM [INV]"
- Amount slider (0-100%)
- Offset slider (-100% to +100%)
- Invert checkbox
- Remove button
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, 
    QPushButton, QCheckBox, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from .crossmod_routing_state import CrossmodConnection

# Import theme if available, otherwise use defaults
try:
    from .theme import COLORS, FONT_FAMILY, FONT_SIZES, MONO_FONT
except ImportError:
    COLORS = {
        'background': '#1a1a1a',
        'background_light': '#2a2a2a',
        'text': '#cccccc',
        'text_bright': '#ffffff',
        'text_dim': '#888888',
        'border': '#444444',
    }
    FONT_FAMILY = 'Arial'
    FONT_SIZES = {'small': 10, 'label': 11, 'section': 12}
    MONO_FONT = 'Courier New'


class CrossmodConnectionPopup(QDialog):
    """Popup for editing crossmod connection parameters."""
    
    # Signals
    connection_changed = pyqtSignal(object)  # Emits CrossmodConnection
    remove_requested = pyqtSignal()
    
    def __init__(self, connection: CrossmodConnection, source_label: str, target_label: str, parent=None):
        super().__init__(parent)
        
        self.connection = connection
        self.source_label = source_label
        self.target_label = target_label
        
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        
        self._setup_ui()
        self._sync_from_connection()
    
    def _setup_ui(self):
        """Build the popup UI."""
        self.setFixedWidth(240)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # Stylesheet
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['background_light']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
            }}
            QLabel {{
                color: {COLORS['text']};
            }}
            QSlider::groove:horizontal {{
                background: {COLORS['background']};
                height: 6px;
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {COLORS['text']};
                width: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }}
            QCheckBox {{
                color: {COLORS['text']};
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
            }}
        """)
        
        # Header: "GEN X → GY PARAM [INV]"
        self.header_label = QLabel()
        self.header_label.setFont(QFont(MONO_FONT, FONT_SIZES['label'], QFont.Bold))
        self.header_label.setStyleSheet(f"color: {COLORS['text_bright']};")
        self._update_header()
        layout.addWidget(self.header_label)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background-color: {COLORS['border']};")
        layout.addWidget(sep)
        
        # Amount slider
        amount_layout = QHBoxLayout()
        amount_label = QLabel("Amount")
        amount_label.setFixedWidth(60)
        self.amount_slider = QSlider(Qt.Horizontal)
        self.amount_slider.setRange(0, 100)
        self.amount_slider.valueChanged.connect(self._on_amount_changed)
        self.amount_value_label = QLabel("50%")
        self.amount_value_label.setFixedWidth(40)
        self.amount_value_label.setAlignment(Qt.AlignRight)
        amount_layout.addWidget(amount_label)
        amount_layout.addWidget(self.amount_slider)
        amount_layout.addWidget(self.amount_value_label)
        layout.addLayout(amount_layout)
        
        # Offset slider
        offset_layout = QHBoxLayout()
        offset_label = QLabel("Offset")
        offset_label.setFixedWidth(60)
        self.offset_slider = QSlider(Qt.Horizontal)
        self.offset_slider.setRange(-100, 100)
        self.offset_slider.valueChanged.connect(self._on_offset_changed)
        self.offset_value_label = QLabel("0%")
        self.offset_value_label.setFixedWidth(40)
        self.offset_value_label.setAlignment(Qt.AlignRight)
        offset_layout.addWidget(offset_label)
        offset_layout.addWidget(self.offset_slider)
        offset_layout.addWidget(self.offset_value_label)
        layout.addLayout(offset_layout)
        
        # Invert checkbox
        self.invert_checkbox = QCheckBox("Invert")
        self.invert_checkbox.stateChanged.connect(self._on_invert_changed)
        layout.addWidget(self.invert_checkbox)
        
        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet(f"background-color: {COLORS['border']};")
        layout.addWidget(sep2)
        
        # Remove button
        self.remove_btn = QPushButton("Remove")
        self.remove_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['background']};
                color: #ff4444;
                border: 1px solid #aa2222;
                border-radius: 3px;
                padding: 5px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #330000;
                color: #ff6666;
                border-color: #ff4444;
            }}
        """)
        self.remove_btn.clicked.connect(self._on_remove_clicked)
        layout.addWidget(self.remove_btn)
    
    def _update_header(self):
        """Update header text with current invert state."""
        inv_suffix = " [INV]" if self.connection.invert else ""
        self.header_label.setText(f"{self.source_label} → {self.target_label}{inv_suffix}")
    
    def _sync_from_connection(self):
        """Sync UI from connection state."""
        self.amount_slider.blockSignals(True)
        self.offset_slider.blockSignals(True)
        self.invert_checkbox.blockSignals(True)
        
        self.amount_slider.setValue(int(self.connection.amount * 100))
        self.offset_slider.setValue(int(self.connection.offset * 100))
        self.invert_checkbox.setChecked(self.connection.invert)
        
        self.amount_value_label.setText(f"{int(self.connection.amount * 100)}%")
        self.offset_value_label.setText(f"{int(self.connection.offset * 100)}%")
        
        self.amount_slider.blockSignals(False)
        self.offset_slider.blockSignals(False)
        self.invert_checkbox.blockSignals(False)
        
        self._update_header()
    
    def sync_from_state(self, conn: CrossmodConnection):
        """External sync from state (when connection changes elsewhere)."""
        self.connection = conn
        self._sync_from_connection()
    
    def _on_amount_changed(self, value: int):
        """Handle amount slider change."""
        self.connection.amount = value / 100.0
        self.amount_value_label.setText(f"{value}%")
        self.connection_changed.emit(self.connection)
    
    def _on_offset_changed(self, value: int):
        """Handle offset slider change."""
        self.connection.offset = value / 100.0
        self.offset_value_label.setText(f"{value}%")
        self.connection_changed.emit(self.connection)
    
    def _on_invert_changed(self, state: int):
        """Handle invert checkbox change."""
        self.connection.invert = (state == Qt.Checked)
        self._update_header()
        self.connection_changed.emit(self.connection)
    
    def _on_remove_clicked(self):
        """Handle remove button click."""
        self.remove_requested.emit()
        self.close()
