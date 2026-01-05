"""
Extended Mod Connection Popup
Dialog for creating/adjusting modulation connections to extended targets (FX/Mod/Send).

Extends the basic popup with target selection tabs.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, 
    QPushButton, QFrame, QTabWidget, QComboBox, QWidget
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

from .mod_routing_state import (
    ModConnection, Polarity, 
    build_mod_target, build_fx_target, build_send_target
)
from .theme import COLORS, FONT_SIZES, MONO_FONT


# Wire key definitions (from backend contract)
FX_PARAMS = {
    'heat': [
        ('type', 'Circuit'),
        ('drive', 'Drive'),
        ('mix', 'Mix'),
    ],
    'echo': [
        ('time', 'Time'),
        ('feedback', 'Feedback'),
        ('tone', 'Tone'),
        ('wow', 'Wow'),
        ('spring', 'Spring'),
    ],
    'reverb': [
        ('size', 'Size'),
        ('decay', 'Decay'),
        ('tone', 'Tone'),
    ],
    'dual_filter': [
        ('drive', 'Drive'),
        ('freq1', 'Freq 1'),
        ('reso1', 'Res 1'),
        ('freq2', 'Freq 2'),
        ('reso2', 'Res 2'),
        ('routing', 'Routing'),
        ('sync1Rate', 'Sync 1'),
        ('sync2Rate', 'Sync 2'),
        ('syncAmt', 'Sync Amt'),
        ('harmonics', 'Harmonics'),
        ('mix', 'Mix'),
    ],
}

MOD_PARAMS = {
    'lfo': [
        ('rate', 'Rate'),
        ('mode', 'Mode'),
        ('shape', 'Shape'),
        ('pattern', 'Pattern'),
        ('rotate', 'Rotate'),
        ('wave_1', 'Wave A'),
        ('wave_2', 'Wave B'),
        ('wave_3', 'Wave C'),
        ('wave_4', 'Wave D'),
        ('pol_1', 'Pol A'),
        ('pol_2', 'Pol B'),
        ('pol_3', 'Pol C'),
        ('pol_4', 'Pol D'),
    ],
    'arseq': [
        ('rate', 'Rate'),
        ('mode', 'Mode'),
        ('clockMode', 'Clock Mode'),
        ('atk_1', 'Attack A'),
        ('atk_2', 'Attack B'),
        ('atk_3', 'Attack C'),
        ('atk_4', 'Attack D'),
        ('rel_1', 'Release A'),
        ('rel_2', 'Release B'),
        ('rel_3', 'Release C'),
        ('rel_4', 'Release D'),
        ('pol_1', 'Pol A'),
        ('pol_2', 'Pol B'),
        ('pol_3', 'Pol C'),
        ('pol_4', 'Pol D'),
    ],
    'sauce': [
        ('rate', 'Rate'),
        ('depth', 'Depth'),
        ('grav', 'Gravity'),
        ('reso', 'Resonance'),
        ('excur', 'Excursion'),
        ('calm', 'Calm'),
        ('tens_1', 'Tension 1'),
        ('tens_2', 'Tension 2'),
        ('tens_3', 'Tension 3'),
        ('tens_4', 'Tension 4'),
        ('mass_1', 'Mass 1'),
        ('mass_2', 'Mass 2'),
        ('mass_3', 'Mass 3'),
        ('mass_4', 'Mass 4'),
        ('pol_1', 'Pol 1'),
        ('pol_2', 'Pol 2'),
        ('pol_3', 'Pol 3'),
        ('pol_4', 'Pol 4'),
    ],
}

SEND_TYPES = [
    ('ec', 'Echo'),
    ('vb', 'Verb'),
]


class ExtModConnectionPopup(QDialog):
    """Popup for creating/editing extended mod connections."""
    
    # Signals
    connection_created = pyqtSignal(object)  # New ModConnection
    connection_changed = pyqtSignal(object)  # Modified ModConnection
    remove_requested = pyqtSignal()          # Remove connection
    
    def __init__(self, source_bus: int, source_label: str, 
                 connection: ModConnection = None, parent=None):
        super().__init__(parent)
        
        self.source_bus = source_bus
        self.source_label = source_label
        self.connection = connection  # None = create mode, not None = edit mode
        self.is_edit_mode = connection is not None
        
        self._syncing = False
        self._pending_update = False
        self._throttle_timer = QTimer(self)
        self._throttle_timer.setSingleShot(True)
        self._throttle_timer.timeout.connect(self._flush_update)
        self._throttle_ms = 16
        
        self.setWindowTitle("Extended Mod Connection")
        self.setModal(False)
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
        
        self._setup_style()
        self._setup_ui()
        
        if self.is_edit_mode:
            self._sync_from_connection()
    
    def _setup_style(self):
        """Apply dark theme."""
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
            QComboBox {{
                background-color: {COLORS['background_light']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 4px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid {COLORS['text']};
                margin-right: 4px;
            }}
            QTabWidget::pane {{
                border: 1px solid {COLORS['border']};
                background: {COLORS['background']};
            }}
            QTabBar::tab {{
                background: {COLORS['background_light']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                padding: 6px 12px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {COLORS['background_highlight']};
                color: {COLORS['text_bright']};
            }}
        """)
    
    def _setup_ui(self):
        """Build the popup UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Header
        header_text = f"{self.source_label} → "
        if self.is_edit_mode:
            header_text += self._get_target_label()
        else:
            header_text += "[Select Target]"
        
        self.header_label = QLabel(header_text)
        self.header_label.setFont(QFont(MONO_FONT, FONT_SIZES['label'], QFont.Bold))
        self.header_label.setStyleSheet(f"color: {COLORS['text_bright']};")
        self.header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.header_label)
        
        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        sep1.setStyleSheet(f"background-color: {COLORS['border']};")
        layout.addWidget(sep1)
        
        # Tab widget (only in create mode)
        if not self.is_edit_mode:
            self.tabs = QTabWidget()
            self.tabs.addTab(self._create_fx_tab(), "FX")
            self.tabs.addTab(self._create_mod_tab(), "Modulator")
            self.tabs.addTab(self._create_send_tab(), "Send")
            layout.addWidget(self.tabs)
            
            # Separator
            sep2 = QFrame()
            sep2.setFrameShape(QFrame.HLine)
            sep2.setStyleSheet(f"background-color: {COLORS['border']};")
            layout.addWidget(sep2)
        
        # Amount/Offset sliders (common to both modes)
        self._add_param_sliders(layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        if self.is_edit_mode:
            # Edit mode: Remove button
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
        else:
            # Create mode: Create + Cancel buttons
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(self.reject)
            button_layout.addWidget(cancel_btn)
            
            create_btn = QPushButton("Create")
            create_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['enabled']};
                    color: {COLORS['background']};
                    min-width: 80px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['accent']};
                }}
            """)
            create_btn.clicked.connect(self._on_create_clicked)
            button_layout.addWidget(create_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Size based on mode
        if self.is_edit_mode:
            self.setFixedSize(280, 170)
        else:
            self.setFixedSize(320, 280)
    
    def _create_fx_tab(self) -> QWidget:
        """Create FX target selection tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        # FX type selector
        fx_layout = QHBoxLayout()
        fx_layout.addWidget(QLabel("FX Unit:"))
        self.fx_type_combo = QComboBox()
        self.fx_type_combo.addItems(["HEAT", "ECHO", "REVERB", "DUAL_FILTER"])
        self.fx_type_combo.currentTextChanged.connect(self._on_fx_type_changed)
        fx_layout.addWidget(self.fx_type_combo, 1)
        layout.addLayout(fx_layout)
        
        # Param selector
        param_layout = QHBoxLayout()
        param_layout.addWidget(QLabel("Param:"))
        self.fx_param_combo = QComboBox()
        param_layout.addWidget(self.fx_param_combo, 1)
        layout.addLayout(param_layout)
        
        layout.addStretch()
        
        # Initialize params for first FX type
        self._on_fx_type_changed("HEAT")
        
        return widget
    
    def _create_mod_tab(self) -> QWidget:
        """Create modulator target selection tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        # Mod slot selector
        slot_layout = QHBoxLayout()
        slot_layout.addWidget(QLabel("Mod Slot:"))
        self.mod_slot_combo = QComboBox()
        self.mod_slot_combo.addItems(["1", "2", "3", "4"])
        slot_layout.addWidget(self.mod_slot_combo, 1)
        layout.addLayout(slot_layout)
        
        # Param selector (TODO: should filter by actual mod type in slot)
        param_layout = QHBoxLayout()
        param_layout.addWidget(QLabel("Param:"))
        self.mod_param_combo = QComboBox()
        # For now, show all possible params (ideally filtered by slot type)
        all_params = set()
        for params in MOD_PARAMS.values():
            all_params.update(params)
        for wire_key, label in sorted(all_params):
            self.mod_param_combo.addItem(label, wire_key)
        param_layout.addWidget(self.mod_param_combo, 1)
        layout.addLayout(param_layout)
        
        layout.addStretch()
        
        return widget
    
    def _create_send_tab(self) -> QWidget:
        """Create send target selection tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        # Channel selector
        chan_layout = QHBoxLayout()
        chan_layout.addWidget(QLabel("Channel:"))
        self.send_chan_combo = QComboBox()
        self.send_chan_combo.addItems([str(i) for i in range(1, 9)])
        chan_layout.addWidget(self.send_chan_combo, 1)
        layout.addLayout(chan_layout)
        
        # Send type selector
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Send:"))
        self.send_type_combo = QComboBox()
        for wire_key, label in SEND_TYPES:
            self.send_type_combo.addItem(label, wire_key)
        type_layout.addWidget(self.send_type_combo, 1)
        layout.addLayout(type_layout)
        
        layout.addStretch()
        
        return widget
    
    def _add_param_sliders(self, layout: QVBoxLayout):
        """Add amount/offset sliders."""
        # Amount
        amount_layout = QHBoxLayout()
        amount_label = QLabel("Amount")
        amount_label.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        amount_label.setFixedWidth(60)
        amount_layout.addWidget(amount_label)
        
        self.amount_slider = QSlider(Qt.Horizontal)
        self.amount_slider.setRange(0, 100)
        self.amount_slider.setValue(50)
        self.amount_slider.valueChanged.connect(self._on_amount_changed)
        amount_layout.addWidget(self.amount_slider, 1)
        
        self.amount_value = QLabel("50%")
        self.amount_value.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        self.amount_value.setFixedWidth(40)
        self.amount_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        amount_layout.addWidget(self.amount_value)
        
        layout.addLayout(amount_layout)
        
        # Offset
        offset_layout = QHBoxLayout()
        offset_label = QLabel("Offset")
        offset_label.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        offset_label.setFixedWidth(60)
        offset_layout.addWidget(offset_label)
        
        self.offset_slider = QSlider(Qt.Horizontal)
        self.offset_slider.setRange(-100, 100)
        self.offset_slider.setValue(0)
        self.offset_slider.valueChanged.connect(self._on_offset_changed)
        offset_layout.addWidget(self.offset_slider, 1)
        
        self.offset_value = QLabel("0%")
        self.offset_value.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        self.offset_value.setFixedWidth(40)
        self.offset_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        offset_layout.addWidget(self.offset_value)
        
        layout.addLayout(offset_layout)
    
    def _on_fx_type_changed(self, fx_name: str):
        """Update FX param list when type changes."""
        self.fx_param_combo.clear()
        fx_key = fx_name.lower()
        for wire_key, label in FX_PARAMS.get(fx_key, []):
            self.fx_param_combo.addItem(label, wire_key)
    
    def _get_target_str(self) -> str:
        """Build target string from current tab selection."""
        if self.is_edit_mode:
            return self.connection.target_str
        
        current_tab = self.tabs.currentIndex()
        
        if current_tab == 0:  # FX
            fx_type = self.fx_type_combo.currentText().lower()
            param = self.fx_param_combo.currentData()
            return build_fx_target(fx_type, param)
        
        elif current_tab == 1:  # Mod
            slot = int(self.mod_slot_combo.currentText())
            param = self.mod_param_combo.currentData()
            return build_mod_target(slot, param)
        
        elif current_tab == 2:  # Send
            slot = int(self.send_chan_combo.currentText())
            send_type = self.send_type_combo.currentData()
            return build_send_target(slot, send_type)
        
        return ""
    
    def _get_target_label(self) -> str:
        """Get human-readable target label."""
        if not self.connection or not self.connection.target_str:
            return "[Unknown]"
        
        parts = self.connection.target_str.split(':')
        if len(parts) < 3:
            return self.connection.target_str
        
        target_type, identifier, param = parts[0], parts[1], parts[2]
        
        if target_type == 'fx':
            fx_labels = {'heat': 'HEAT', 'echo': 'ECHO', 'reverb': 'REVERB', 'dual_filter': 'DUAL_FILTER'}
            fx_name = fx_labels.get(identifier, identifier.upper())
            param_label = param.title()
            return f"{fx_name} {param_label}"
        
        elif target_type == 'mod':
            param_label = param.replace('_', ' ').title()
            return f"MOD {identifier} {param_label}"
        
        elif target_type == 'send':
            send_labels = {'ec': 'Echo', 'vb': 'Verb'}
            send_name = send_labels.get(param, param.upper())
            return f"CH{identifier} {send_name}"
        
        return self.connection.target_str
    
    def _sync_from_connection(self):
        """Set UI from existing connection."""
        if not self.connection:
            return
        
        self._syncing = True
        self.amount_slider.blockSignals(True)
        self.offset_slider.blockSignals(True)
        
        self.amount_slider.setValue(int(self.connection.amount * 100))
        self.offset_slider.setValue(int(self.connection.offset * 100))
        
        self.amount_slider.blockSignals(False)
        self.offset_slider.blockSignals(False)
        
        self._update_value_labels()
        self._syncing = False
    
    def _update_value_labels(self):
        """Update percentage labels."""
        amount = self.amount_slider.value()
        offset = self.offset_slider.value()
        
        self.amount_value.setText(f"{amount}%")
        sign = "+" if offset > 0 else ""
        self.offset_value.setText(f"{sign}{offset}%")
    
    def _on_amount_changed(self, value: int):
        """Handle amount slider change."""
        self._update_value_labels()
        if self.is_edit_mode and not self._syncing:
            self.connection.amount = value / 100.0
            self._schedule_update()
    
    def _on_offset_changed(self, value: int):
        """Handle offset slider change."""
        self._update_value_labels()
        if self.is_edit_mode and not self._syncing:
            self.connection.offset = value / 100.0
            self._schedule_update()
    
    def _schedule_update(self):
        """Schedule throttled update emission."""
        self._pending_update = True
        if not self._throttle_timer.isActive():
            self._throttle_timer.start(self._throttle_ms)
    
    def _flush_update(self):
        """Emit pending update."""
        if self._pending_update:
            self._pending_update = False
            if self.is_edit_mode:
                self.connection_changed.emit(self.connection)
    
    def _on_create_clicked(self):
        """Create new connection."""
        target_str = self._get_target_str()
        if not target_str:
            return
        
        new_conn = ModConnection(
            source_bus=self.source_bus,
            target_str=target_str,
            amount=self.amount_slider.value() / 100.0,
            offset=self.offset_slider.value() / 100.0,
            depth=1.0,
            polarity=Polarity.BIPOLAR,
            invert=False
        )
        
        self.connection_created.emit(new_conn)
        self.accept()
    
    def _on_remove_clicked(self):
        """Request connection removal."""
        self.remove_requested.emit()
        self.accept()
    
    def closeEvent(self, event):
        """Flush pending updates on close."""
        self._flush_update()
        super().closeEvent(event)
