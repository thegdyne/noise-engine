"""
Mod Connection Popup
Dialog for adjusting modulation connection parameters.

Layout:
┌─────────────────────────────┐
│  M1.A → G1 CUT              │  Header
├─────────────────────────────┤
│  Amount   [━━━━━●━━━] 50%   │  Horizontal slider 0-100%
│  Offset   [━━━━━━━━●] 0%    │  Horizontal slider -100% to +100%
├─────────────────────────────┤
│         [Remove]            │  Red button
└─────────────────────────────┘

All changes update SC in real-time via signals.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, 
    QPushButton, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QEvent
from PyQt5.QtGui import QFont

from .mod_routing_state import ModConnection
from .theme import COLORS, FONT_SIZES, MONO_FONT


class ModConnectionPopup(QDialog):
    """Popup dialog for adjusting mod connection parameters."""
    
    # Signals
    connection_changed = pyqtSignal(object)  # Emits ModConnection on any change
    remove_requested = pyqtSignal()          # Remove connection
    
    def __init__(self, connection: ModConnection, source_label: str, target_label: str, 
                 get_target_value=None, parent=None):
        super().__init__(parent)
        
        self.connection = connection
        self.source_label = source_label  # e.g. "M1.A"
        self.target_label = target_label  # e.g. "G1 CUT"
        self.get_target_value = get_target_value  # Callback returning 0-1 slider value
        self._syncing = False  # Prevent feedback during sync
        
        # Throttle timer for OSC updates
        self._pending_update = False
        self._throttle_timer = QTimer(self)
        self._throttle_timer.setSingleShot(True)
        self._throttle_timer.timeout.connect(self._flush_update)
        self._throttle_ms = 16  # ~60Hz max
        
        self.setWindowTitle("Mod Connection")
        self.setFixedSize(280, 170)
        self.setModal(False)  # Non-modal so user can hear changes
        
        # Tool window: stays with parent, doesn't appear in task switcher
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
        
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
        
        # Offset slider row (-100% to +100%)
        offset_layout = QHBoxLayout()
        offset_label = QLabel("Offset")
        offset_label.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        offset_label.setFixedWidth(50)
        offset_layout.addWidget(offset_label)
        
        self.offset_slider = QSlider(Qt.Horizontal)
        self.offset_slider.setRange(-100, 100)
        self.offset_slider.valueChanged.connect(self._on_offset_changed)
        self.offset_slider.installEventFilter(self)  # For double-click reset
        offset_layout.addWidget(self.offset_slider, 1)
        
        self.offset_value = QLabel("0%")
        self.offset_value.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        self.offset_value.setFixedWidth(40)
        self.offset_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        offset_layout.addWidget(self.offset_value)
        
        layout.addLayout(offset_layout)
        
        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet(f"background-color: {COLORS['border']};")
        layout.addWidget(sep2)
        
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
        """Set UI state from connection (blocks signals to avoid feedback loop)."""
        self._syncing = True
        
        # Always ensure depth is 1.0 and polarity is bipolar (we only use amount/offset now)
        self.connection.depth = 1.0
        
        # Block signals while syncing to avoid triggering change events
        self.amount_slider.blockSignals(True)
        self.offset_slider.blockSignals(True)
        
        self.amount_slider.setValue(int(self.connection.amount * 100))
        self.offset_slider.setValue(int(self.connection.offset * 100))
        
        self.amount_slider.blockSignals(False)
        self.offset_slider.blockSignals(False)
        
        self._update_value_labels()
        self._syncing = False
    
    def sync_from_state(self, conn: ModConnection):
        """Update popup to reflect external changes to the connection."""
        # Only update if this is our connection
        if (conn.source_bus == self.connection.source_bus and
            conn.target_slot == self.connection.target_slot and
            conn.target_param == self.connection.target_param):
            self.connection = conn
            self._sync_from_connection()
        
    def _update_value_labels(self):
        """Update the percentage labels."""
        self.amount_value.setText(f"{int(self.connection.amount * 100)}%")
        # Offset shows sign
        offset_pct = int(self.connection.offset * 100)
        sign = "+" if offset_pct > 0 else ""
        self.offset_value.setText(f"{sign}{offset_pct}%")
        
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
            
    def _on_amount_changed(self, value: int):
        """Handle amount slider change."""
        self.connection.amount = value / 100.0
        self._update_value_labels()
        self._schedule_update()
    
    def _on_offset_changed(self, value: int):
        """Handle offset slider change."""
        self.connection.offset = value / 100.0
        self._update_value_labels()
        self._schedule_update()
        
    def _on_remove_clicked(self):
        """Request connection removal."""
        self.remove_requested.emit()
        self.accept()
    
    def eventFilter(self, obj, event):
        """Handle double-click on offset slider to reset to 0."""
        if obj == self.offset_slider and event.type() == QEvent.MouseButtonDblClick:
            self.offset_slider.setValue(0)
            return True
        return super().eventFilter(obj, event)
        
    def closeEvent(self, event):
        """Flush any pending updates on close."""
        self._flush_update()
        super().closeEvent(event)
