"""
FX Slot Component - UI Refresh Phase 2
Single FX slot with type selector and p1-p4 sliders

Follows the flat absolute positioning pattern from generator_slot.py
"""

from PyQt5.QtWidgets import QWidget, QLabel, QFrame, QSizePolicy
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from .widgets import DragSlider, CycleButton
from .theme import COLORS, FONT_FAMILY, MONO_FONT, FONT_SIZES, button_style

from src.config import (
    FX_SLOT_TYPES, FX_SLOT_PARAM_LABELS, FX_SLOT_DEFAULTS, FX_SLOT_DEFAULT_TYPES
)
from src.utils.logger import logger


# =============================================================================
# LAYOUT - All positions in one place
# =============================================================================
SLOT_LAYOUT = {
    'slot_width': 145,
    'slot_height': 150,

    # Header
    'id_label_x': 5, 'id_label_y': 4,
    'id_label_w': 30, 'id_label_h': 18,
    'selector_x': 28, 'selector_y': 2,
    'selector_w': 81, 'selector_h': 20,

    # Bypass button
    'bypass_x': 111, 'bypass_y': 2,
    'bypass_w': 32, 'bypass_h': 20,

    # Separator
    'sep_y': 24,

    # Sliders (p1-p4 + return)
    'slider_y': 32,
    'slider_h': 80,
    'slider_w': 18,
    'slider_label_h': 12,

    'p1_x': 6,
    'p2_x': 34,
    'p3_x': 62,
    'p4_x': 90,
    'ret_x': 120,  # Return slider

    # Bottom row labels
    'label_y': 118,
}

L = SLOT_LAYOUT


class FXSlot(QWidget):
    """Single FX slot with type selector and p1-p4 sliders."""

    # Signals
    type_changed = pyqtSignal(int, str)  # slot_id, fx_type
    param_changed = pyqtSignal(int, str, float)  # slot_id, param (p1/p2/p3/p4/return), value
    bypass_changed = pyqtSignal(int, bool)  # slot_id, bypassed

    def __init__(self, slot_id, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.slot_id = slot_id
        self.setObjectName(f"fx_slot_{slot_id}")

        # State
        self.fx_type = FX_SLOT_DEFAULT_TYPES[slot_id - 1] if slot_id <= len(FX_SLOT_DEFAULT_TYPES) else 'Empty'
        self.bypassed = False
        self.osc_bridge = None

        self.setFixedSize(L['slot_width'], L['slot_height'])
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # Storage
        self.sliders = {}
        self.slider_labels = {}

        self._build_ui()
        self.update_style()

    def _build_ui(self):
        """Build all widgets with absolute positioning."""

        # ----- HEADER -----
        self.id_label = QLabel(f"FX{self.slot_id}", self)
        self.id_label.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
        self.id_label.setStyleSheet(f"color: {COLORS['accent_effect']};")
        self.id_label.setGeometry(L['id_label_x'], L['id_label_y'],
                                   L['id_label_w'], L['id_label_h'])

        # Type selector
        self.type_btn = CycleButton(FX_SLOT_TYPES, parent=self)
        self.type_btn.setGeometry(L['selector_x'], L['selector_y'],
                                   L['selector_w'], L['selector_h'])
        self.type_btn.value_changed.connect(self._on_type_changed)
        self.type_btn.setFont(QFont(MONO_FONT, FONT_SIZES["small"]))
        self.type_btn.setStyleSheet(button_style("submenu"))
        self.type_btn.set_value(self.fx_type)

        # Bypass button
        self.bypass_btn = CycleButton(['ON', 'BYP'], parent=self)
        self.bypass_btn.setGeometry(L['bypass_x'], L['bypass_y'],
                                     L['bypass_w'], L['bypass_h'])
        self.bypass_btn.value_changed.connect(self._on_bypass_changed)
        self.bypass_btn.setFont(QFont(MONO_FONT, FONT_SIZES["tiny"]))
        self._update_bypass_style()

        # ----- SEPARATOR -----
        self.separator = QFrame(self)
        self.separator.setGeometry(4, L['sep_y'], L['slot_width'] - 8, 1)
        self.separator.setStyleSheet(f"background-color: {COLORS['border_light']};")

        # ----- SLIDERS -----
        param_labels = FX_SLOT_PARAM_LABELS.get(self.fx_type, ['P1', 'P2', 'P3', 'P4'])
        defaults = FX_SLOT_DEFAULTS.get(self.fx_type, [0.5, 0.5, 0.5, 0.5])

        # p1-p4 sliders
        slider_positions = [
            ('p1', L['p1_x'], param_labels[0], defaults[0]),
            ('p2', L['p2_x'], param_labels[1], defaults[1]),
            ('p3', L['p3_x'], param_labels[2], defaults[2]),
            ('p4', L['p4_x'], param_labels[3], defaults[3]),
        ]

        for key, x, label_text, default_val in slider_positions:
            slider = DragSlider(parent=self)
            slider.setObjectName(f"fx_slot{self.slot_id}_{key}")
            slider.setGeometry(x, L['slider_y'], L['slider_w'], L['slider_h'])
            slider.setMinimum(0)
            slider.setMaximum(1000)
            slider.setValue(int(default_val * 1000))
            slider.valueChanged.connect(lambda v, k=key: self._on_param_changed(k, v / 1000.0))
            self.sliders[key] = slider

            # Label below slider
            label = QLabel(label_text, self)
            label.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
            label.setStyleSheet(f"color: {COLORS['text_dim']};")
            label.setAlignment(Qt.AlignCenter)
            label.setGeometry(x - 4, L['label_y'], L['slider_w'] + 8, L['slider_label_h'])
            self.slider_labels[key] = label

        # Return slider (always present)
        ret_slider = DragSlider(parent=self)
        ret_slider.setObjectName(f"fx_slot{self.slot_id}_return")
        ret_slider.setGeometry(L['ret_x'], L['slider_y'], L['slider_w'], L['slider_h'])
        ret_slider.setMinimum(0)
        ret_slider.setMaximum(1000)
        ret_slider.setValue(500)  # 50% default
        ret_slider.valueChanged.connect(lambda v: self._on_param_changed('return', v / 1000.0))
        self.sliders['return'] = ret_slider

        ret_label = QLabel("RET", self)
        ret_label.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        ret_label.setStyleSheet(f"color: {COLORS['text_dim']};")
        ret_label.setAlignment(Qt.AlignCenter)
        ret_label.setGeometry(L['ret_x'] - 2, L['label_y'], L['slider_w'] + 4, L['slider_label_h'])
        self.slider_labels['return'] = ret_label

    def _on_type_changed(self, new_type):
        """Handle FX type change."""
        old_type = self.fx_type
        self.fx_type = new_type

        # Update slider labels
        param_labels = FX_SLOT_PARAM_LABELS.get(new_type, ['P1', 'P2', 'P3', 'P4'])
        for i, key in enumerate(['p1', 'p2', 'p3', 'p4']):
            self.slider_labels[key].setText(param_labels[i])

        # Reset to default values for new type
        defaults = FX_SLOT_DEFAULTS.get(new_type, [0.5, 0.5, 0.5, 0.5])
        for i, key in enumerate(['p1', 'p2', 'p3', 'p4']):
            self.sliders[key].blockSignals(True)
            self.sliders[key].setValue(int(defaults[i] * 1000))
            self.sliders[key].blockSignals(False)

        # Enable/disable sliders based on type
        is_empty = (new_type == 'Empty')
        for key in ['p1', 'p2', 'p3', 'p4', 'return']:
            self.sliders[key].setEnabled(not is_empty)

        self.update_style()

        # Emit signal
        self.type_changed.emit(self.slot_id, new_type)

        # Send OSC (use SSOT key format: fx_slotN_param)
        if self.osc_bridge:
            self.osc_bridge.send(f'fx_slot{self.slot_id}_type', new_type.lower())

        logger.debug(f"FX Slot {self.slot_id}: {old_type} -> {new_type}", component="FX")

    def _on_param_changed(self, param_key, value):
        """Handle parameter change."""
        self.param_changed.emit(self.slot_id, param_key, value)

        # Send OSC (use SSOT key format: fx_slotN_param)
        if self.osc_bridge:
            self.osc_bridge.send(f'fx_slot{self.slot_id}_{param_key}', value)

    def _on_bypass_changed(self, state):
        """Handle bypass toggle."""
        self.bypassed = (state == 'BYP')
        self._update_bypass_style()
        self.bypass_changed.emit(self.slot_id, self.bypassed)

        # Send OSC (use SSOT key format: fx_slotN_param)
        if self.osc_bridge:
            self.osc_bridge.send(f'fx_slot{self.slot_id}_bypass', 1.0 if self.bypassed else 0.0)

    def _update_bypass_style(self):
        """Update bypass button appearance."""
        if self.bypassed:
            self.bypass_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['warning']};
                    color: {COLORS['warning_text']};
                    border-radius: 3px;
                }}
            """)
        else:
            self.bypass_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['enabled']};
                    color: {COLORS['enabled_text']};
                    border-radius: 3px;
                }}
            """)

    def update_style(self):
        """Update slot appearance based on state."""
        if self.fx_type == 'Empty':
            border_color = COLORS['border']
            bg_color = COLORS['background']
        else:
            border_color = COLORS['accent_effect_dim']
            bg_color = COLORS['background_light']

        self.setStyleSheet(f"""
            FXSlot {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 4px;
            }}
        """)

    def set_osc_bridge(self, bridge):
        """Set OSC bridge for sending messages."""
        self.osc_bridge = bridge

    def set_type(self, fx_type):
        """Programmatically set FX type."""
        if fx_type in FX_SLOT_TYPES:
            self.type_btn.set_value(fx_type)
            self._on_type_changed(fx_type)

    def set_param(self, param_key, value):
        """Programmatically set a parameter value."""
        if param_key in self.sliders:
            self.sliders[param_key].blockSignals(True)
            self.sliders[param_key].setValue(int(value * 1000))
            self.sliders[param_key].blockSignals(False)

    def get_state(self):
        """Get current slot state for preset saving."""
        return {
            'type': self.fx_type,
            'bypassed': self.bypassed,
            'p1': self.sliders['p1'].value() / 1000.0,
            'p2': self.sliders['p2'].value() / 1000.0,
            'p3': self.sliders['p3'].value() / 1000.0,
            'p4': self.sliders['p4'].value() / 1000.0,
            'return': self.sliders['return'].value() / 1000.0,
        }

    def load_state(self, state):
        """Load slot state from preset."""
        # Accept both 'fx_type' (schema) and 'type' (legacy) keys
        if 'fx_type' in state:
            self.set_type(state['fx_type'])
        elif 'type' in state:
            self.set_type(state['type'])
        if 'bypassed' in state:
            self.bypassed = state['bypassed']
            self.bypass_btn.set_value('BYP' if self.bypassed else 'ON')
            self._update_bypass_style()
        for key in ['p1', 'p2', 'p3', 'p4']:
            if key in state:
                self.set_param(key, state[key])
        # Accept both 'return_level' (schema) and 'return' (legacy) keys
        if 'return_level' in state:
            self.set_param('return', state['return_level'])
        elif 'return' in state:
            self.set_param('return', state['return'])
