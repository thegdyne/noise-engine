"""
Mod Connection Popup
Dialog for adjusting modulation connection parameters.

Layout:
┌─────────────────────────────┐
│  M1.A → G1 CUT              │  Header
├─────────────────────────────┤
│  Depth    [━━━━━●━━━] 60%   │  Horizontal slider 0-100%
│  Amount   [━━━━━━━━●] 100%  │  Horizontal slider 0-100%
├─────────────────────────────┤
│  [Bi] [U+] [U-]      [INV]  │  Polarity + invert toggle
├─────────────────────────────┤
│         [Remove]            │  Red button
└─────────────────────────────┘

All changes update SC in real-time via signals.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, 
    QPushButton, QFrame, QButtonGroup
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

from .mod_routing_state import ModConnection, Polarity
from .theme import COLORS, FONT_SIZES, MONO_FONT


class ModConnectionPopup(QDialog):
    """Popup dialog for adjusting mod connection parameters."""
    
    # Signals
    connection_changed = pyqtSignal(object)  # Emits ModConnection on any change
    remove_requested = pyqtSignal()          # Remove connection
    
    def __init__(self, connection: ModConnection, source_label: str, target_label: str, parent=None):
        super().__init__(parent)
        
        self.connection = connection
        self.source_label = source_label  # e.g. "M1.A"
        self.target_label = target_label  # e.g. "G1 CUT"
        
        # Throttle timer for OSC updates
        self._pending_update = False
        self._throttle_timer = QTimer(self)
        self._throttle_timer.setSingleShot(True)
        self._throttle_timer.timeout.connect(self._flush_update)
        self._throttle_ms = 16  # ~60Hz max
        
        self.setWindowTitle("Mod Connection")
        self.setFixedSize(280, 220)
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
                padding: 4px 8px;
                min-width: 32px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['background_highlight']};
            }}
            QPushButton:checked {{
                background-color: {COLORS['enabled']};
                color: {COLORS['background']};
            }}
            QSlider::groove:horizontal {{
                height: 6px;
                background: {COLORS['background_light']};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                width: 14px;
                margin: -4px 0;
                background: {COLORS['enabled']};
                border-radius: 7px;
            }}
            QSlider::sub-page:horizontal {{
                background: {COLORS['enabled']};
                border-radius: 3px;
            }}
        """)
        
        self._setup_ui()
        self._sync_from_connection()
        
    def _setup_ui(self):
        """Build the popup UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Header: connection info
        header = QLabel(f"{self.source_label} → {self.target_label}")
        header.setFont(QFont(MONO_FONT, FONT_SIZES['label'], QFont.Bold))
        header.setStyleSheet(f"color: {COLORS['text_bright']};")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        sep1.setStyleSheet(f"background-color: {COLORS['border']};")
        layout.addWidget(sep1)
        
        # Depth slider row
        depth_layout = QHBoxLayout()
        depth_label = QLabel("Depth")
        depth_label.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        depth_label.setFixedWidth(50)
        depth_layout.addWidget(depth_label)
        
        self.depth_slider = QSlider(Qt.Horizontal)
        self.depth_slider.setRange(0, 100)
        self.depth_slider.valueChanged.connect(self._on_depth_changed)
        depth_layout.addWidget(self.depth_slider, 1)
        
        self.depth_value = QLabel("50%")
        self.depth_value.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        self.depth_value.setFixedWidth(40)
        self.depth_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        depth_layout.addWidget(self.depth_value)
        
        layout.addLayout(depth_layout)
        
        # Amount slider row
        amount_layout = QHBoxLayout()
        amount_label = QLabel("Amount")
        amount_label.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        amount_label.setFixedWidth(50)
        amount_layout.addWidget(amount_label)
        
        self.amount_slider = QSlider(Qt.Horizontal)
        self.amount_slider.setRange(0, 100)
        self.amount_slider.valueChanged.connect(self._on_amount_changed)
        amount_layout.addWidget(self.amount_slider, 1)
        
        self.amount_value = QLabel("100%")
        self.amount_value.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        self.amount_value.setFixedWidth(40)
        self.amount_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        amount_layout.addWidget(self.amount_value)
        
        layout.addLayout(amount_layout)
        
        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet(f"background-color: {COLORS['border']};")
        layout.addWidget(sep2)
        
        # Polarity + Invert row
        polarity_layout = QHBoxLayout()
        polarity_layout.setSpacing(4)
        
        # Polarity buttons (mutually exclusive)
        self.polarity_group = QButtonGroup(self)
        
        self.btn_bipolar = QPushButton("Bi")
        self.btn_bipolar.setCheckable(True)
        self.btn_bipolar.setToolTip("Bipolar: sweeps above and below center")
        self.polarity_group.addButton(self.btn_bipolar, 0)
        polarity_layout.addWidget(self.btn_bipolar)
        
        self.btn_uni_pos = QPushButton("U+")
        self.btn_uni_pos.setCheckable(True)
        self.btn_uni_pos.setToolTip("Unipolar+: only sweeps above center")
        self.polarity_group.addButton(self.btn_uni_pos, 1)
        polarity_layout.addWidget(self.btn_uni_pos)
        
        self.btn_uni_neg = QPushButton("U−")
        self.btn_uni_neg.setCheckable(True)
        self.btn_uni_neg.setToolTip("Unipolar−: only sweeps below center")
        self.polarity_group.addButton(self.btn_uni_neg, 2)
        polarity_layout.addWidget(self.btn_uni_neg)
        
        self.polarity_group.buttonClicked.connect(self._on_polarity_changed)
        
        polarity_layout.addStretch()
        
        # Invert toggle
        self.btn_invert = QPushButton("INV")
        self.btn_invert.setCheckable(True)
        self.btn_invert.setToolTip("Invert: flip modulation signal")
        self.btn_invert.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['background_light']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['background_highlight']};
            }}
            QPushButton:checked {{
                background-color: #ff6600;
                color: {COLORS['background']};
            }}
        """)
        self.btn_invert.clicked.connect(self._on_invert_changed)
        polarity_layout.addWidget(self.btn_invert)
        
        layout.addLayout(polarity_layout)
        
        # Separator
        sep3 = QFrame()
        sep3.setFrameShape(QFrame.HLine)
        sep3.setStyleSheet(f"background-color: {COLORS['border']};")
        layout.addWidget(sep3)
        
        # Remove button (centered)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        remove_btn = QPushButton("Remove")
        remove_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #661111;
                color: {COLORS['text']};
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: #881111;
            }}
        """)
        remove_btn.clicked.connect(self._on_remove_clicked)
        button_layout.addWidget(remove_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
    def _sync_from_connection(self):
        """Set UI state from connection."""
        self.depth_slider.setValue(int(self.connection.depth * 100))
        self.amount_slider.setValue(int(self.connection.amount * 100))
        
        # Polarity buttons
        polarity_btn = self.polarity_group.button(self.connection.polarity.value)
        if polarity_btn:
            polarity_btn.setChecked(True)
        
        # Invert
        self.btn_invert.setChecked(self.connection.invert)
        
        self._update_value_labels()
        
    def _update_value_labels(self):
        """Update the percentage labels."""
        self.depth_value.setText(f"{int(self.connection.depth * 100)}%")
        self.amount_value.setText(f"{int(self.connection.amount * 100)}%")
        
    def _schedule_update(self):
        """Schedule a throttled update emission."""
        self._pending_update = True
        if not self._throttle_timer.isActive():
            self._throttle_timer.start(self._throttle_ms)
            
    def _flush_update(self):
        """Emit the pending update."""
        if self._pending_update:
            self._pending_update = False
            self.connection_changed.emit(self.connection)
            
    def _on_depth_changed(self, value: int):
        """Handle depth slider change."""
        self.connection.depth = value / 100.0
        self._update_value_labels()
        self._schedule_update()
        
    def _on_amount_changed(self, value: int):
        """Handle amount slider change."""
        self.connection.amount = value / 100.0
        self._update_value_labels()
        self._schedule_update()
        
    def _on_polarity_changed(self, button):
        """Handle polarity button change."""
        polarity_id = self.polarity_group.id(button)
        self.connection.polarity = Polarity(polarity_id)
        self._schedule_update()
        
    def _on_invert_changed(self):
        """Handle invert toggle."""
        self.connection.invert = self.btn_invert.isChecked()
        self._schedule_update()
        
    def _on_remove_clicked(self):
        """Request connection removal."""
        self.remove_requested.emit()
        self.accept()
        
    def closeEvent(self, event):
        """Flush any pending updates on close."""
        self._flush_update()
        super().closeEvent(event)
