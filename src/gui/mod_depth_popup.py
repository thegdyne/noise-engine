"""
Mod Depth Popup
Dialog for adjusting modulation connection depth.

Shows:
- Connection info header (e.g. "M1.A → G1 CUT")
- Horizontal slider: -100% to +100%
- Current value display
- Buttons: Disable/Enable, Remove, Close
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, 
    QPushButton, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from .mod_routing_state import ModConnection
from .theme import COLORS, FONT_FAMILY, FONT_SIZES, MONO_FONT


class ModDepthPopup(QDialog):
    """Popup dialog for adjusting mod connection depth."""
    
    # Signals
    depth_changed = pyqtSignal(float)      # New depth value
    enable_toggled = pyqtSignal(bool)      # Enable/disable toggled
    remove_requested = pyqtSignal()        # Remove connection
    
    def __init__(self, connection: ModConnection, source_label: str, target_label: str, parent=None):
        super().__init__(parent)
        
        self.connection = connection
        self.source_label = source_label  # e.g. "M1.A"
        self.target_label = target_label  # e.g. "G1 CUT"
        
        self.setWindowTitle("Mod Depth")
        self.setFixedSize(320, 180)
        self.setModal(False)  # Non-modal so user can hear changes
        
        # Dark theme
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['background']};
                border: 2px solid {COLORS['border_light']};
            }}
            QLabel {{
                color: {COLORS['text']};
            }}
            QPushButton {{
                background-color: {COLORS['background_light']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 6px 12px;
                min-width: 70px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['background_highlight']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['enabled']};
            }}
            QSlider::groove:horizontal {{
                height: 8px;
                background: {COLORS['background_light']};
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                width: 18px;
                margin: -5px 0;
                background: {COLORS['enabled']};
                border-radius: 9px;
            }}
            QSlider::sub-page:horizontal {{
                background: {COLORS['enabled']};
                border-radius: 4px;
            }}
        """)
        
        self._setup_ui()
        self._update_display()
        
    def _setup_ui(self):
        """Build the popup UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        # Header: connection info
        header = QLabel(f"{self.source_label} → {self.target_label}")
        header.setFont(QFont(MONO_FONT, FONT_SIZES['label'], QFont.Bold))
        header.setStyleSheet(f"color: {COLORS['text_bright']};")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background-color: {COLORS['border']};")
        layout.addWidget(sep)
        
        # Depth slider section
        slider_layout = QHBoxLayout()
        
        # Min label
        min_label = QLabel("-100%")
        min_label.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        min_label.setStyleSheet(f"color: {COLORS['text_dim']};")
        slider_layout.addWidget(min_label)
        
        # Slider: -100 to +100 (maps to -1.0 to +1.0)
        self.depth_slider = QSlider(Qt.Horizontal)
        self.depth_slider.setRange(-100, 100)
        self.depth_slider.setValue(int(self.connection.depth * 100))
        self.depth_slider.setTickPosition(QSlider.TicksBelow)
        self.depth_slider.setTickInterval(25)
        self.depth_slider.valueChanged.connect(self._on_slider_changed)
        slider_layout.addWidget(self.depth_slider, 1)
        
        # Max label
        max_label = QLabel("+100%")
        max_label.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        max_label.setStyleSheet(f"color: {COLORS['text_dim']};")
        slider_layout.addWidget(max_label)
        
        layout.addLayout(slider_layout)
        
        # Current value display
        self.value_label = QLabel()
        self.value_label.setFont(QFont(MONO_FONT, FONT_SIZES['section'], QFont.Bold))
        self.value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.value_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        # Enable/Disable button
        self.enable_btn = QPushButton()
        self.enable_btn.clicked.connect(self._on_enable_clicked)
        button_layout.addWidget(self.enable_btn)
        
        # Remove button
        remove_btn = QPushButton("Remove")
        remove_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #661111;
                color: {COLORS['text']};
            }}
            QPushButton:hover {{
                background-color: #881111;
            }}
        """)
        remove_btn.clicked.connect(self._on_remove_clicked)
        button_layout.addWidget(remove_btn)
        
        button_layout.addStretch()
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
    def _update_display(self):
        """Update value display and button states."""
        depth_pct = int(self.connection.depth * 100)
        sign = "+" if depth_pct >= 0 else ""
        self.value_label.setText(f"{sign}{depth_pct}%")
        
        # Colour based on depth
        if self.connection.depth > 0:
            color = COLORS['enabled']  # Green for positive
        elif self.connection.depth < 0:
            color = '#ff6600'  # Orange for inverted
        else:
            color = COLORS['text_dim']
        self.value_label.setStyleSheet(f"color: {color};")
        
        # Enable button text
        if self.connection.enabled:
            self.enable_btn.setText("Disable")
        else:
            self.enable_btn.setText("Enable")
            
    def _on_slider_changed(self, value: int):
        """Handle slider value change."""
        new_depth = value / 100.0
        self.connection.depth = new_depth
        self._update_display()
        self.depth_changed.emit(new_depth)
        
    def _on_enable_clicked(self):
        """Toggle enable state."""
        self.connection.enabled = not self.connection.enabled
        self._update_display()
        self.enable_toggled.emit(self.connection.enabled)
        
    def _on_remove_clicked(self):
        """Request connection removal."""
        self.remove_requested.emit()
        self.accept()
        
    def set_depth(self, depth: float):
        """Set depth value (called externally)."""
        self.connection.depth = depth
        self.depth_slider.setValue(int(depth * 100))
        self._update_display()
