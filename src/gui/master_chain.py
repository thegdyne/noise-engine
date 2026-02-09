"""
Master Chain Component - Phase 3 Flat Layout Redesign
Unified master section: Heat → Filter → EQ → Comp → Limiter → Output

All modules use flat absolute positioning for visual consistency.
Standard module height: 150px (matching FX slots)
"""

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QFrame, QPushButton, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPainter, QColor, QLinearGradient

from .theme import COLORS, MONO_FONT, FONT_FAMILY, FONT_SIZES, get
from .widgets import DragSlider, CycleButton
from src.config import OSC_PATHS, CLOCK_RATES, CLOCK_DEFAULT_INDEX

# =============================================================================
# SHARED CONSTANTS
# =============================================================================

MODULE_HEIGHT = 150  # Standard height for all bottom bar modules

def bypass_btn_style(bypassed: bool) -> str:
    """Return bypass button stylesheet."""
    if bypassed:
        return f"""
            QPushButton {{
                background-color: {COLORS['warning']};
                color: {COLORS['warning_text']};
                border: 1px solid {COLORS['border']};
                border-radius: 2px;
            }}
        """
    else:
        return f"""
            QPushButton {{
                background-color: {COLORS['enabled']};
                color: {COLORS['enabled_text']};
                border: 1px solid {COLORS['border_active']};
                border-radius: 2px;
            }}
        """

def small_btn_style() -> str:
    """Return small button stylesheet."""
    return f"""
        QPushButton {{
            background-color: {COLORS['background_dark']};
            color: {COLORS['text']};
            border: 1px solid {COLORS['border']};
            border-radius: 2px;
            padding: 0px;
        }}
        QPushButton:hover {{
            border-color: {COLORS['text_dim']};
        }}
    """


# =============================================================================
# HEAT MODULE - Flat Layout
# =============================================================================

HEAT_LAYOUT = {
    'width': 70,
    'height': MODULE_HEIGHT,

    # Header
    'title_x': 5, 'title_y': 4, 'title_w': 32, 'title_h': 16,
    'bypass_x': 38, 'bypass_y': 3, 'bypass_w': 28, 'bypass_h': 18,

    # Separator
    'sep_y': 24,

    # Sliders
    'slider_y': 32, 'slider_h': 80, 'slider_w': 18,
    'drv_x': 10,
    'mix_x': 40,

    # Labels
    'label_y': 116, 'label_h': 12,

    # Circuit button
    'circuit_x': 5, 'circuit_y': 130, 'circuit_w': 60, 'circuit_h': 16,
}

HL = HEAT_LAYOUT


class HeatModule(QWidget):
    """Heat saturation module with flat absolute positioning."""

    CIRCUITS = ["CLN", "TAPE", "TUBE", "CRSH"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("master_heat")

        self.circuit_index = 0
        self.bypassed = True
        self.osc_bridge = None

        self.setFixedSize(HL['width'], HL['height'])
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self._build_ui()
        self._update_style()

    def _build_ui(self):
        """Build all widgets with absolute positioning."""

        # Title
        self.title = QLabel("HEAT", self)
        self.title.setFont(QFont(FONT_FAMILY, FONT_SIZES['tiny'], QFont.Bold))
        self.title.setStyleSheet(f"color: {get('accent_master')};")
        self.title.setGeometry(HL['title_x'], HL['title_y'], HL['title_w'], HL['title_h'])

        # Bypass button (CycleButton for drag support)
        self.bypass_btn = CycleButton(["BYP", "ON"], initial_index=0, parent=self)
        self.bypass_btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['micro']))
        self.bypass_btn.setGeometry(HL['bypass_x'], HL['bypass_y'], HL['bypass_w'], HL['bypass_h'])
        self.bypass_btn.index_changed.connect(self._on_bypass_changed)
        self._update_bypass_style()

        # Separator
        self.separator = QFrame(self)
        self.separator.setGeometry(4, HL['sep_y'], HL['width'] - 8, 1)
        self.separator.setStyleSheet(f"background-color: {get('accent_master_dim')};")

        # Drive slider
        self.drive_slider = DragSlider(parent=self)
        self.drive_slider.setObjectName("fx_heat_drive")
        self.drive_slider.setGeometry(HL['drv_x'], HL['slider_y'], HL['slider_w'], HL['slider_h'])
        self.drive_slider.setMinimum(0)
        self.drive_slider.setMaximum(200)
        self.drive_slider.setValue(0)
        self.drive_slider.setToolTip("Drive amount")
        self.drive_slider.valueChanged.connect(self._on_drive_changed)

        drv_lbl = QLabel("DRV", self)
        drv_lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        drv_lbl.setStyleSheet(f"color: {COLORS['text_dim']};")
        drv_lbl.setAlignment(Qt.AlignCenter)
        drv_lbl.setGeometry(HL['drv_x'] - 4, HL['label_y'], HL['slider_w'] + 8, HL['label_h'])

        # Mix slider
        self.mix_slider = DragSlider(parent=self)
        self.mix_slider.setObjectName("fx_heat_mix")
        self.mix_slider.setGeometry(HL['mix_x'], HL['slider_y'], HL['slider_w'], HL['slider_h'])
        self.mix_slider.setMinimum(0)
        self.mix_slider.setMaximum(200)
        self.mix_slider.setValue(100)
        self.mix_slider.setToolTip("Dry/Wet mix")
        self.mix_slider.valueChanged.connect(self._on_mix_changed)

        mix_lbl = QLabel("MIX", self)
        mix_lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        mix_lbl.setStyleSheet(f"color: {COLORS['text_dim']};")
        mix_lbl.setAlignment(Qt.AlignCenter)
        mix_lbl.setGeometry(HL['mix_x'] - 4, HL['label_y'], HL['slider_w'] + 8, HL['label_h'])

        # Circuit button (CycleButton for drag support)
        self.circuit_btn = CycleButton(self.CIRCUITS, initial_index=0, parent=self)
        self.circuit_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        self.circuit_btn.setGeometry(HL['circuit_x'], HL['circuit_y'], HL['circuit_w'], HL['circuit_h'])
        self.circuit_btn.setToolTip("Saturation circuit type (drag to change)")
        self.circuit_btn.index_changed.connect(self._on_circuit_changed)
        self.circuit_btn.setStyleSheet(small_btn_style())

    def _update_style(self):
        """Update module frame style."""
        self.setStyleSheet(f"""
            QWidget#master_heat {{
                background-color: {COLORS['background']};
                border: 1px solid {get('accent_master_dim')};
                border-radius: 4px;
            }}
        """)

    def _on_bypass_changed(self, index):
        self.bypassed = (index == 0)  # 0=BYP (bypassed), 1=ON (not bypassed)
        self._update_bypass_style()
        self._send_osc(OSC_PATHS['heat_bypass'], 1 if self.bypassed else 0)

    def _update_bypass_style(self):
        self.bypass_btn.setStyleSheet(bypass_btn_style(self.bypassed))

    def _on_circuit_changed(self, index):
        self.circuit_index = index
        self._send_osc(OSC_PATHS['heat_circuit'], self.circuit_index)

    def _on_drive_changed(self, value):
        self._send_osc(OSC_PATHS['heat_drive'], value / 200.0)

    def _on_mix_changed(self, value):
        self._send_osc(OSC_PATHS['heat_mix'], value / 200.0)

    def set_osc_bridge(self, osc_bridge):
        self.osc_bridge = osc_bridge

    def _send_osc(self, path, value):
        if self.osc_bridge and self.osc_bridge.client:
            self.osc_bridge.client.send_message(path, [value])

    def sync_state(self):
        self._send_osc(OSC_PATHS['heat_bypass'], 1 if self.bypassed else 0)
        self._send_osc(OSC_PATHS['heat_circuit'], self.circuit_index)
        self._send_osc(OSC_PATHS['heat_drive'], self.drive_slider.value() / 200.0)
        self._send_osc(OSC_PATHS['heat_mix'], self.mix_slider.value() / 200.0)

    def get_state(self) -> dict:
        return {
            'bypass': self.bypassed,
            'circuit': self.circuit_index,
            'drive': self.drive_slider.value(),
            'mix': self.mix_slider.value(),
        }

    def set_state(self, state: dict):
        if 'bypass' in state:
            self.bypassed = state['bypass']
            self.bypass_btn.set_index(0 if self.bypassed else 1)
            self._update_bypass_style()
            self._send_osc(OSC_PATHS['heat_bypass'], 1 if self.bypassed else 0)
        if 'circuit' in state:
            self.circuit_index = state['circuit']
            self.circuit_btn.set_index(self.circuit_index)
            self._send_osc(OSC_PATHS['heat_circuit'], self.circuit_index)
        if 'drive' in state:
            self.drive_slider.setValue(state['drive'])
        if 'mix' in state:
            self.mix_slider.setValue(state['mix'])


# =============================================================================
# FILTER MODULE - Flat Layout
# =============================================================================

FILTER_LAYOUT = {
    'width': 186,
    'height': MODULE_HEIGHT,

    # Header
    'title_x': 5, 'title_y': 4, 'title_w': 32, 'title_h': 16,
    'bypass_x': 88, 'bypass_y': 3, 'bypass_w': 28, 'bypass_h': 18,

    # Separator
    'sep_y': 24,

    # Sliders (F1, R1, F2, R2, MIX)
    'slider_y': 32, 'slider_h': 70, 'slider_w': 16,
    'f1_x': 8,
    'r1_x': 30,
    'f2_x': 54,
    'r2_x': 76,
    'mix_x': 98,

    # Labels
    'label_y': 106, 'label_h': 12,

    # Mode buttons (below F1 and F2 labels)
    'mode_y': 118, 'mode_w': 20, 'mode_h': 14,

    # Routing button
    'routing_x': 30, 'routing_y': 132, 'routing_w': 40, 'routing_h': 14,

    # Sync section (right side) — vertical separator + F1/F2 rate buttons + AMT slider
    'sync_sep_x': 119,
    'sync_lbl_x': 124, 'sync_lbl_y': 4, 'sync_lbl_w': 60, 'sync_lbl_h': 16,
    'sync_btn_w': 36, 'sync_btn_h': 18,
    'sync_f1_x': 126, 'sync_f1_y': 32,
    'sync_f2_x': 126, 'sync_f2_y': 56,
    'sync_f1_lbl_x': 164, 'sync_f1_lbl_y': 34,
    'sync_f2_lbl_x': 164, 'sync_f2_lbl_y': 58,
    'sync_amt_x': 144, 'sync_amt_y': 82, 'sync_amt_w': 18, 'sync_amt_h': 50,
    'sync_amt_lbl_y': 134,
}

FL = FILTER_LAYOUT

# Sync modes: OFF + SSOT clock rates
FILTER_SYNC_MODES = ["OFF"] + CLOCK_RATES
FILTER_SYNC_CLK_INDEX = 1 + CLOCK_DEFAULT_INDEX  # OFF shifts SSOT indices by +1
assert FILTER_SYNC_MODES[0] == "OFF"
assert FILTER_SYNC_MODES[FILTER_SYNC_CLK_INDEX] == "CLK"


class FilterModule(QWidget):
    """Dual filter module with flat absolute positioning, includes sync controls."""

    MODES = ["LP", "BP", "HP"]
    ROUTINGS = ["SER", "PAR"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("master_filter")

        self.f1_mode = 0
        self.f2_mode = 0
        self.routing = 0
        self.bypassed = True
        self.osc_bridge = None
        self.f1_sync_prev_index = 0
        self.f2_sync_prev_index = 0

        self.setFixedSize(FL['width'], FL['height'])
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self._build_ui()
        self._update_style()

    def _build_ui(self):
        """Build all widgets with absolute positioning."""

        # Title
        self.title = QLabel("FILT", self)
        self.title.setFont(QFont(FONT_FAMILY, FONT_SIZES['tiny'], QFont.Bold))
        self.title.setStyleSheet(f"color: {get('accent_master')};")
        self.title.setGeometry(FL['title_x'], FL['title_y'], FL['title_w'], FL['title_h'])

        # Bypass button (CycleButton for drag support)
        self.bypass_btn = CycleButton(["BYP", "ON"], initial_index=0, parent=self)
        self.bypass_btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['micro']))
        self.bypass_btn.setGeometry(FL['bypass_x'], FL['bypass_y'], FL['bypass_w'], FL['bypass_h'])
        self.bypass_btn.index_changed.connect(self._on_bypass_changed)
        self._update_bypass_style()

        # Separator
        self.separator = QFrame(self)
        self.separator.setGeometry(4, FL['sep_y'], FL['width'] - 8, 1)
        self.separator.setStyleSheet(f"background-color: {get('accent_master_dim')};")

        # F1 slider
        self.f1_slider = DragSlider(parent=self)
        self.f1_slider.setObjectName("fx_fb_freq1")
        self.f1_slider.setGeometry(FL['f1_x'], FL['slider_y'], FL['slider_w'], FL['slider_h'])
        self.f1_slider.setMinimum(0)
        self.f1_slider.setMaximum(200)
        self.f1_slider.setValue(120)
        self.f1_slider.setToolTip("Filter 1 frequency")
        self.f1_slider.valueChanged.connect(self._on_f1_changed)

        f1_lbl = QLabel("F1", self)
        f1_lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        f1_lbl.setStyleSheet(f"color: {COLORS['text_dim']};")
        f1_lbl.setAlignment(Qt.AlignCenter)
        f1_lbl.setGeometry(FL['f1_x'] - 2, FL['label_y'], FL['slider_w'] + 4, FL['label_h'])

        # F1 mode button (CycleButton for drag support)
        self.f1_mode_btn = CycleButton(self.MODES, initial_index=0, parent=self)
        self.f1_mode_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        self.f1_mode_btn.setGeometry(FL['f1_x'] - 2, FL['mode_y'], FL['mode_w'], FL['mode_h'])
        self.f1_mode_btn.index_changed.connect(self._on_f1_mode_changed)
        self.f1_mode_btn.setStyleSheet(small_btn_style())

        # R1 slider
        self.r1_slider = DragSlider(parent=self)
        self.r1_slider.setObjectName("fx_fb_reso1")
        self.r1_slider.setGeometry(FL['r1_x'], FL['slider_y'], FL['slider_w'], FL['slider_h'])
        self.r1_slider.setMinimum(0)
        self.r1_slider.setMaximum(200)
        self.r1_slider.setValue(60)
        self.r1_slider.setToolTip("Filter 1 resonance")
        self.r1_slider.valueChanged.connect(self._on_r1_changed)

        r1_lbl = QLabel("R1", self)
        r1_lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        r1_lbl.setStyleSheet(f"color: {COLORS['text_dim']};")
        r1_lbl.setAlignment(Qt.AlignCenter)
        r1_lbl.setGeometry(FL['r1_x'] - 2, FL['label_y'], FL['slider_w'] + 4, FL['label_h'])

        # F2 slider
        self.f2_slider = DragSlider(parent=self)
        self.f2_slider.setObjectName("fx_fb_freq2")
        self.f2_slider.setGeometry(FL['f2_x'], FL['slider_y'], FL['slider_w'], FL['slider_h'])
        self.f2_slider.setMinimum(0)
        self.f2_slider.setMaximum(200)
        self.f2_slider.setValue(120)
        self.f2_slider.setToolTip("Filter 2 frequency")
        self.f2_slider.valueChanged.connect(self._on_f2_changed)

        f2_lbl = QLabel("F2", self)
        f2_lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        f2_lbl.setStyleSheet(f"color: {COLORS['text_dim']};")
        f2_lbl.setAlignment(Qt.AlignCenter)
        f2_lbl.setGeometry(FL['f2_x'] - 2, FL['label_y'], FL['slider_w'] + 4, FL['label_h'])

        # F2 mode button (CycleButton for drag support)
        self.f2_mode_btn = CycleButton(self.MODES, initial_index=0, parent=self)
        self.f2_mode_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        self.f2_mode_btn.setGeometry(FL['f2_x'] - 2, FL['mode_y'], FL['mode_w'], FL['mode_h'])
        self.f2_mode_btn.index_changed.connect(self._on_f2_mode_changed)
        self.f2_mode_btn.setStyleSheet(small_btn_style())

        # R2 slider
        self.r2_slider = DragSlider(parent=self)
        self.r2_slider.setObjectName("fx_fb_reso2")
        self.r2_slider.setGeometry(FL['r2_x'], FL['slider_y'], FL['slider_w'], FL['slider_h'])
        self.r2_slider.setMinimum(0)
        self.r2_slider.setMaximum(200)
        self.r2_slider.setValue(60)
        self.r2_slider.setToolTip("Filter 2 resonance")
        self.r2_slider.valueChanged.connect(self._on_r2_changed)

        r2_lbl = QLabel("R2", self)
        r2_lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        r2_lbl.setStyleSheet(f"color: {COLORS['text_dim']};")
        r2_lbl.setAlignment(Qt.AlignCenter)
        r2_lbl.setGeometry(FL['r2_x'] - 2, FL['label_y'], FL['slider_w'] + 4, FL['label_h'])

        # MIX slider (wet/dry)
        self.mix_slider = DragSlider(parent=self)
        self.mix_slider.setObjectName("fx_fb_mix")
        self.mix_slider.setGeometry(FL['mix_x'], FL['slider_y'], FL['slider_w'], FL['slider_h'])
        self.mix_slider.setMinimum(0)
        self.mix_slider.setMaximum(200)
        self.mix_slider.setValue(200)  # Default 100% wet
        self.mix_slider.setToolTip("Filter wet/dry mix")
        self.mix_slider.valueChanged.connect(self._on_mix_changed)

        mix_lbl = QLabel("MX", self)
        mix_lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        mix_lbl.setStyleSheet(f"color: {COLORS['text_dim']};")
        mix_lbl.setAlignment(Qt.AlignCenter)
        mix_lbl.setGeometry(FL['mix_x'] - 2, FL['label_y'], FL['slider_w'] + 4, FL['label_h'])

        # Routing button (CycleButton for drag support)
        self.routing_btn = CycleButton(self.ROUTINGS, initial_index=0, parent=self)
        self.routing_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        self.routing_btn.setGeometry(FL['routing_x'], FL['routing_y'], FL['routing_w'], FL['routing_h'])
        self.routing_btn.setToolTip("Serial/Parallel routing (drag to change)")
        self.routing_btn.index_changed.connect(self._on_routing_changed)
        self.routing_btn.setStyleSheet(small_btn_style())

        # === SYNC SECTION (right side) ===

        # Vertical separator
        self.sync_sep = QFrame(self)
        self.sync_sep.setGeometry(FL['sync_sep_x'], FL['sep_y'], 1, FL['height'] - FL['sep_y'] - 4)
        self.sync_sep.setStyleSheet(f"background-color: {get('accent_master_dim')};")

        # Sync label
        sync_lbl = QLabel("SYNC", self)
        sync_lbl.setFont(QFont(FONT_FAMILY, FONT_SIZES['tiny'], QFont.Bold))
        sync_lbl.setStyleSheet(f"color: {get('accent_master')};")
        sync_lbl.setGeometry(FL['sync_lbl_x'], FL['sync_lbl_y'], FL['sync_lbl_w'], FL['sync_lbl_h'])

        # F1 sync button
        self.f1_sync_btn = CycleButton(FILTER_SYNC_MODES, initial_index=0, parent=self)
        self.f1_sync_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        self.f1_sync_btn.setGeometry(FL['sync_f1_x'], FL['sync_f1_y'], FL['sync_btn_w'], FL['sync_btn_h'])
        self.f1_sync_btn.setToolTip("F1 sync: click for CLK, drag to change rate")
        self.f1_sync_btn.wrap = True
        self.f1_sync_btn.index_changed.connect(self._on_f1_sync_changed)
        self._update_sync_btn_style(self.f1_sync_btn, 0)

        f1_sync_lbl = QLabel("F1", self)
        f1_sync_lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        f1_sync_lbl.setStyleSheet(f"color: {COLORS['text_dim']};")
        f1_sync_lbl.setGeometry(FL['sync_f1_lbl_x'], FL['sync_f1_lbl_y'], 20, 14)

        # F2 sync button
        self.f2_sync_btn = CycleButton(FILTER_SYNC_MODES, initial_index=0, parent=self)
        self.f2_sync_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        self.f2_sync_btn.setGeometry(FL['sync_f2_x'], FL['sync_f2_y'], FL['sync_btn_w'], FL['sync_btn_h'])
        self.f2_sync_btn.setToolTip("F2 sync: click for CLK, drag to change rate")
        self.f2_sync_btn.wrap = True
        self.f2_sync_btn.index_changed.connect(self._on_f2_sync_changed)
        self._update_sync_btn_style(self.f2_sync_btn, 0)

        f2_sync_lbl = QLabel("F2", self)
        f2_sync_lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        f2_sync_lbl.setStyleSheet(f"color: {COLORS['text_dim']};")
        f2_sync_lbl.setGeometry(FL['sync_f2_lbl_x'], FL['sync_f2_lbl_y'], 20, 14)

        # AMT slider
        self.amt_slider = DragSlider(parent=self)
        self.amt_slider.setObjectName("fx_fb_syncAmt")
        self.amt_slider.setGeometry(FL['sync_amt_x'], FL['sync_amt_y'], FL['sync_amt_w'], FL['sync_amt_h'])
        self.amt_slider.setMinimum(0)
        self.amt_slider.setMaximum(200)
        self.amt_slider.setValue(0)
        self.amt_slider.setToolTip("Clock sync modulation depth")
        self.amt_slider.valueChanged.connect(self._on_amt_changed)

        amt_lbl = QLabel("AMT", self)
        amt_lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        amt_lbl.setStyleSheet(f"color: {COLORS['text_dim']};")
        amt_lbl.setAlignment(Qt.AlignCenter)
        amt_lbl.setGeometry(FL['sync_amt_x'] - 6, FL['sync_amt_lbl_y'], 30, 12)

    def _update_style(self):
        self.setStyleSheet(f"""
            QWidget#master_filter {{
                background-color: {COLORS['background']};
                border: 1px solid {get('accent_master_dim')};
                border-radius: 4px;
            }}
        """)

    def _on_bypass_changed(self, index):
        self.bypassed = (index == 0)  # 0=BYP (bypassed), 1=ON (not bypassed)
        self._update_bypass_style()
        self._send_osc(OSC_PATHS['fb_bypass'], 1 if self.bypassed else 0)

    def _update_bypass_style(self):
        self.bypass_btn.setStyleSheet(bypass_btn_style(self.bypassed))

    def _on_f1_mode_changed(self, index):
        self.f1_mode = index
        self._send_osc(OSC_PATHS['fb_mode1'], self.f1_mode)

    def _on_f2_mode_changed(self, index):
        self.f2_mode = index
        self._send_osc(OSC_PATHS['fb_mode2'], self.f2_mode)

    def _on_routing_changed(self, index):
        self.routing = index
        self._send_osc(OSC_PATHS['fb_routing'], self.routing)

    def _on_f1_changed(self, value):
        self._send_osc(OSC_PATHS['fb_freq1'], value / 200.0)

    def _on_r1_changed(self, value):
        self._send_osc(OSC_PATHS['fb_reso1'], value / 200.0)

    def _on_f2_changed(self, value):
        self._send_osc(OSC_PATHS['fb_freq2'], value / 200.0)

    def _on_r2_changed(self, value):
        self._send_osc(OSC_PATHS['fb_reso2'], value / 200.0)

    def _on_mix_changed(self, value):
        self._send_osc(OSC_PATHS['fb_mix'], value / 200.0)

    def _update_sync_btn_style(self, btn, index):
        """Update sync button appearance based on mode."""
        if index == 0:  # FREE
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['background_dark']};
                    color: {COLORS['text_dim']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 3px;
                }}
            """)
        else:  # Synced
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {get('accent_master_dim')};
                    color: {COLORS['text']};
                    border: 1px solid {get('accent_master')};
                    border-radius: 3px;
                }}
            """)

    def _on_f1_sync_changed(self, index):
        if self.f1_sync_prev_index == 0 and index != 0:
            index = FILTER_SYNC_CLK_INDEX
            self.f1_sync_btn.set_index(index)
        self.f1_sync_prev_index = index
        self._update_sync_btn_style(self.f1_sync_btn, index)
        # Send integer idx: FREE -> -1, else (index - 1) aligns with SC clock registry 0..12
        sc_idx = -1 if index == 0 else (index - 1)
        self._send_osc(OSC_PATHS['fb_sync1'], sc_idx)

    def _on_f2_sync_changed(self, index):
        if self.f2_sync_prev_index == 0 and index != 0:
            index = FILTER_SYNC_CLK_INDEX
            self.f2_sync_btn.set_index(index)
        self.f2_sync_prev_index = index
        self._update_sync_btn_style(self.f2_sync_btn, index)
        # Send integer idx: FREE -> -1, else (index - 1) aligns with SC clock registry 0..12
        sc_idx = -1 if index == 0 else (index - 1)
        self._send_osc(OSC_PATHS['fb_sync2'], sc_idx)

    def _on_amt_changed(self, value):
        self._send_osc(OSC_PATHS['fb_sync_amt'], value / 200.0)

    def set_osc_bridge(self, osc_bridge):
        self.osc_bridge = osc_bridge

    def _send_osc(self, path, value):
        if self.osc_bridge and self.osc_bridge.client:
            self.osc_bridge.client.send_message(path, [value])

    def sync_state(self):
        self._send_osc(OSC_PATHS['fb_bypass'], 1 if self.bypassed else 0)
        self._send_osc(OSC_PATHS['fb_mode1'], self.f1_mode)
        self._send_osc(OSC_PATHS['fb_mode2'], self.f2_mode)
        self._send_osc(OSC_PATHS['fb_routing'], self.routing)
        self._send_osc(OSC_PATHS['fb_freq1'], self.f1_slider.value() / 200.0)
        self._send_osc(OSC_PATHS['fb_reso1'], self.r1_slider.value() / 200.0)
        self._send_osc(OSC_PATHS['fb_freq2'], self.f2_slider.value() / 200.0)
        self._send_osc(OSC_PATHS['fb_reso2'], self.r2_slider.value() / 200.0)
        self._send_osc(OSC_PATHS['fb_mix'], self.mix_slider.value() / 200.0)
        # Sync — send integer idx: FREE -> -1, else (btn.index - 1) for SC 0..12
        sc_idx1 = -1 if self.f1_sync_btn.index == 0 else (self.f1_sync_btn.index - 1)
        sc_idx2 = -1 if self.f2_sync_btn.index == 0 else (self.f2_sync_btn.index - 1)
        self._send_osc(OSC_PATHS['fb_sync1'], sc_idx1)
        self._send_osc(OSC_PATHS['fb_sync2'], sc_idx2)
        self._send_osc(OSC_PATHS['fb_sync_amt'], self.amt_slider.value() / 200.0)

    def get_state(self) -> dict:
        return {
            'bypass': self.bypassed,
            'f1_mode': self.f1_mode,
            'f2_mode': self.f2_mode,
            'routing': self.routing,
            'f1': self.f1_slider.value(),
            'r1': self.r1_slider.value(),
            'f2': self.f2_slider.value(),
            'r2': self.r2_slider.value(),
            'mix': self.mix_slider.value(),
            'f1_sync': FILTER_SYNC_MODES[self.f1_sync_btn.index],
            'f2_sync': FILTER_SYNC_MODES[self.f2_sync_btn.index],
            'amt': self.amt_slider.value(),
        }

    def set_state(self, state: dict):
        if 'bypass' in state:
            self.bypassed = state['bypass']
            self.bypass_btn.set_index(0 if self.bypassed else 1)
            self._update_bypass_style()
            self._send_osc(OSC_PATHS['fb_bypass'], 1 if self.bypassed else 0)
        if 'f1_mode' in state:
            self.f1_mode = state['f1_mode']
            self.f1_mode_btn.set_index(self.f1_mode)
            self._send_osc(OSC_PATHS['fb_mode1'], self.f1_mode)
        if 'f2_mode' in state:
            self.f2_mode = state['f2_mode']
            self.f2_mode_btn.set_index(self.f2_mode)
            self._send_osc(OSC_PATHS['fb_mode2'], self.f2_mode)
        if 'routing' in state:
            self.routing = state['routing']
            self.routing_btn.set_index(self.routing)
            self._send_osc(OSC_PATHS['fb_routing'], self.routing)
        if 'f1' in state:
            self.f1_slider.setValue(state['f1'])
        if 'r1' in state:
            self.r1_slider.setValue(state['r1'])
        if 'f2' in state:
            self.f2_slider.setValue(state['f2'])
        if 'r2' in state:
            self.r2_slider.setValue(state['r2'])
        if 'mix' in state:
            self.mix_slider.setValue(state['mix'])
        # Sync state
        if 'f1_sync' in state:
            label = state['f1_sync']
            if isinstance(label, int):
                idx = label if 0 <= label < len(FILTER_SYNC_MODES) else 0
            elif label == "FREE":
                idx = 0  # Legacy: FREE → OFF (index 0)
            else:
                idx = FILTER_SYNC_MODES.index(label) if label in FILTER_SYNC_MODES else 0
            self.f1_sync_btn.set_index(idx)
            self.f1_sync_prev_index = idx
            self._update_sync_btn_style(self.f1_sync_btn, idx)
        if 'f2_sync' in state:
            label = state['f2_sync']
            if isinstance(label, int):
                idx = label if 0 <= label < len(FILTER_SYNC_MODES) else 0
            elif label == "FREE":
                idx = 0  # Legacy: FREE → OFF (index 0)
            else:
                idx = FILTER_SYNC_MODES.index(label) if label in FILTER_SYNC_MODES else 0
            self.f2_sync_btn.set_index(idx)
            self.f2_sync_prev_index = idx
            self._update_sync_btn_style(self.f2_sync_btn, idx)
        if 'amt' in state:
            self.amt_slider.setValue(state['amt'])




# =============================================================================
# EQ MODULE - Flat Layout (3-band DJ isolator)
# =============================================================================

EQ_LAYOUT = {
    'width': 90,
    'height': MODULE_HEIGHT,

    # Header
    'title_x': 5, 'title_y': 4, 'title_w': 24, 'title_h': 16,
    'bypass_x': 58, 'bypass_y': 3, 'bypass_w': 28, 'bypass_h': 18,

    # Separator
    'sep_y': 24,

    # Sliders (LO, MID, HI)
    'slider_y': 32, 'slider_h': 60, 'slider_w': 18,
    'lo_x': 8,
    'mid_x': 36,
    'hi_x': 64,

    # Labels
    'label_y': 96, 'label_h': 12,

    # Kill buttons
    'kill_y': 110, 'kill_w': 22, 'kill_h': 14,

    # Locut button
    'locut_x': 20, 'locut_y': 130, 'locut_w': 50, 'locut_h': 16,
}

EL = EQ_LAYOUT


class EQModule(QWidget):
    """3-band DJ isolator EQ with flat absolute positioning."""

    eq_lo_changed = pyqtSignal(float)
    eq_mid_changed = pyqtSignal(float)
    eq_hi_changed = pyqtSignal(float)
    eq_lo_kill_changed = pyqtSignal(int)
    eq_mid_kill_changed = pyqtSignal(int)
    eq_hi_kill_changed = pyqtSignal(int)
    eq_locut_changed = pyqtSignal(int)
    eq_bypass_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("master_eq")

        self.bypassed = False
        self.lo_kill = 0
        self.mid_kill = 0
        self.hi_kill = 0
        self.locut = 0

        self.setFixedSize(EL['width'], EL['height'])
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self._build_ui()
        self._update_style()

    def _build_ui(self):
        # Title
        self.title = QLabel("EQ", self)
        self.title.setFont(QFont(FONT_FAMILY, FONT_SIZES['tiny'], QFont.Bold))
        self.title.setStyleSheet(f"color: {get('accent_master')};")
        self.title.setGeometry(EL['title_x'], EL['title_y'], EL['title_w'], EL['title_h'])

        # Bypass button (CycleButton for drag support)
        self.bypass_btn = CycleButton(["ON", "BYP"], initial_index=0, parent=self)
        self.bypass_btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['micro']))
        self.bypass_btn.setGeometry(EL['bypass_x'], EL['bypass_y'], EL['bypass_w'], EL['bypass_h'])
        self.bypass_btn.index_changed.connect(self._on_bypass_changed)
        self._update_bypass_style()

        # Separator
        self.separator = QFrame(self)
        self.separator.setGeometry(4, EL['sep_y'], EL['width'] - 8, 1)
        self.separator.setStyleSheet(f"background-color: {get('accent_master_dim')};")

        # LO slider
        self.lo_slider = DragSlider(parent=self)
        self.lo_slider.setObjectName("master_eq_lo")
        self.lo_slider.setGeometry(EL['lo_x'], EL['slider_y'], EL['slider_w'], EL['slider_h'])
        self.lo_slider.setMinimum(0)
        self.lo_slider.setMaximum(240)  # -12 to +12 dB
        self.lo_slider.setValue(120)  # 0 dB
        self.lo_slider.setDoubleClickValue(120)
        self.lo_slider.setToolTip("Low band")
        self.lo_slider.valueChanged.connect(self._on_lo_changed)

        lo_lbl = QLabel("LO", self)
        lo_lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        lo_lbl.setStyleSheet(f"color: {COLORS['text_dim']};")
        lo_lbl.setAlignment(Qt.AlignCenter)
        lo_lbl.setGeometry(EL['lo_x'] - 2, EL['label_y'], EL['slider_w'] + 4, EL['label_h'])

        # LO kill button (CycleButton for drag support)
        self.lo_kill_btn = CycleButton(["—", "CUT"], initial_index=0, parent=self)
        self.lo_kill_btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['micro']))
        self.lo_kill_btn.setGeometry(EL['lo_x'] - 2, EL['kill_y'], EL['kill_w'], EL['kill_h'])
        self.lo_kill_btn.index_changed.connect(self._on_lo_kill_changed)
        self._update_kill_style(self.lo_kill_btn, self.lo_kill)

        # MID slider
        self.mid_slider = DragSlider(parent=self)
        self.mid_slider.setObjectName("master_eq_mid")
        self.mid_slider.setGeometry(EL['mid_x'], EL['slider_y'], EL['slider_w'], EL['slider_h'])
        self.mid_slider.setMinimum(0)
        self.mid_slider.setMaximum(240)
        self.mid_slider.setValue(120)
        self.mid_slider.setDoubleClickValue(120)
        self.mid_slider.setToolTip("Mid band")
        self.mid_slider.valueChanged.connect(self._on_mid_changed)

        mid_lbl = QLabel("MID", self)
        mid_lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        mid_lbl.setStyleSheet(f"color: {COLORS['text_dim']};")
        mid_lbl.setAlignment(Qt.AlignCenter)
        mid_lbl.setGeometry(EL['mid_x'] - 4, EL['label_y'], EL['slider_w'] + 8, EL['label_h'])

        # MID kill button (CycleButton for drag support)
        self.mid_kill_btn = CycleButton(["—", "CUT"], initial_index=0, parent=self)
        self.mid_kill_btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['micro']))
        self.mid_kill_btn.setGeometry(EL['mid_x'] - 2, EL['kill_y'], EL['kill_w'], EL['kill_h'])
        self.mid_kill_btn.index_changed.connect(self._on_mid_kill_changed)
        self._update_kill_style(self.mid_kill_btn, self.mid_kill)

        # HI slider
        self.hi_slider = DragSlider(parent=self)
        self.hi_slider.setObjectName("master_eq_hi")
        self.hi_slider.setGeometry(EL['hi_x'], EL['slider_y'], EL['slider_w'], EL['slider_h'])
        self.hi_slider.setMinimum(0)
        self.hi_slider.setMaximum(240)
        self.hi_slider.setValue(120)
        self.hi_slider.setDoubleClickValue(120)
        self.hi_slider.setToolTip("High band")
        self.hi_slider.valueChanged.connect(self._on_hi_changed)

        hi_lbl = QLabel("HI", self)
        hi_lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        hi_lbl.setStyleSheet(f"color: {COLORS['text_dim']};")
        hi_lbl.setAlignment(Qt.AlignCenter)
        hi_lbl.setGeometry(EL['hi_x'] - 2, EL['label_y'], EL['slider_w'] + 4, EL['label_h'])

        # HI kill button (CycleButton for drag support)
        self.hi_kill_btn = CycleButton(["—", "CUT"], initial_index=0, parent=self)
        self.hi_kill_btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['micro']))
        self.hi_kill_btn.setGeometry(EL['hi_x'] - 2, EL['kill_y'], EL['kill_w'], EL['kill_h'])
        self.hi_kill_btn.index_changed.connect(self._on_hi_kill_changed)
        self._update_kill_style(self.hi_kill_btn, self.hi_kill)

        # Locut button (CycleButton for drag support)
        self.locut_btn = CycleButton(["—", "75Hz"], initial_index=0, parent=self)
        self.locut_btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['micro']))
        self.locut_btn.setGeometry(EL['locut_x'], EL['locut_y'], EL['locut_w'], EL['locut_h'])
        self.locut_btn.setToolTip("Low cut filter (75Hz)")
        self.locut_btn.index_changed.connect(self._on_locut_changed)
        self._update_locut_style()

    def _update_style(self):
        self.setStyleSheet(f"""
            QWidget#master_eq {{
                background-color: {COLORS['background']};
                border: 1px solid {get('accent_master_dim')};
                border-radius: 4px;
            }}
        """)

    def _on_bypass_changed(self, index):
        self.bypassed = (index == 1)  # 0=ON, 1=BYP
        self._update_bypass_style()
        self.eq_bypass_changed.emit(1 if self.bypassed else 0)

    def _update_bypass_style(self):
        self.bypass_btn.setStyleSheet(bypass_btn_style(self.bypassed))

    def _update_kill_style(self, btn, killed):
        if killed:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['warning']};
                    color: {COLORS['warning_text']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 2px;
                }}
            """)
        else:
            btn.setStyleSheet(small_btn_style())

    def _update_locut_style(self):
        if self.locut:
            self.locut_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['enabled']};
                    color: {COLORS['enabled_text']};
                    border: 1px solid {COLORS['border_active']};
                    border-radius: 2px;
                }}
            """)
        else:
            self.locut_btn.setStyleSheet(small_btn_style())

    def _on_lo_kill_changed(self, index):
        self.lo_kill = index  # 0=off, 1=cut
        self._update_kill_style(self.lo_kill_btn, self.lo_kill)
        self.eq_lo_kill_changed.emit(self.lo_kill)

    def _on_mid_kill_changed(self, index):
        self.mid_kill = index  # 0=off, 1=cut
        self._update_kill_style(self.mid_kill_btn, self.mid_kill)
        self.eq_mid_kill_changed.emit(self.mid_kill)

    def _on_hi_kill_changed(self, index):
        self.hi_kill = index  # 0=off, 1=cut
        self._update_kill_style(self.hi_kill_btn, self.hi_kill)
        self.eq_hi_kill_changed.emit(self.hi_kill)

    def _on_locut_changed(self, index):
        self.locut = index  # 0=off, 1=on
        self._update_locut_style()
        self.eq_locut_changed.emit(self.locut)

    def _on_lo_changed(self, value):
        db = (value - 120) / 10.0  # -12 to +12 dB
        self.eq_lo_changed.emit(db)

    def _on_mid_changed(self, value):
        db = (value - 120) / 10.0
        self.eq_mid_changed.emit(db)

    def _on_hi_changed(self, value):
        db = (value - 120) / 10.0
        self.eq_hi_changed.emit(db)

    def get_state(self) -> dict:
        return {
            'bypass': self.bypassed,
            'lo': self.lo_slider.value(),
            'mid': self.mid_slider.value(),
            'hi': self.hi_slider.value(),
            'lo_kill': self.lo_kill,
            'mid_kill': self.mid_kill,
            'hi_kill': self.hi_kill,
            'locut': self.locut,
        }

    def set_state(self, state: dict):
        if 'bypass' in state:
            self.bypassed = state['bypass']
            self.bypass_btn.set_index(1 if self.bypassed else 0)
            self._update_bypass_style()
            self.eq_bypass_changed.emit(1 if self.bypassed else 0)
        if 'lo' in state:
            self.lo_slider.setValue(state['lo'])
        if 'mid' in state:
            self.mid_slider.setValue(state['mid'])
        if 'hi' in state:
            self.hi_slider.setValue(state['hi'])
        if 'lo_kill' in state:
            self.lo_kill_btn.set_index(state['lo_kill'])
        if 'mid_kill' in state:
            self.mid_kill_btn.set_index(state['mid_kill'])
        if 'hi_kill' in state:
            self.hi_kill_btn.set_index(state['hi_kill'])
        if 'locut' in state:
            self.locut_btn.set_index(state['locut'])


# =============================================================================
# COMPRESSOR MODULE - Flat Layout
# =============================================================================

COMP_LAYOUT = {
    'width': 130,
    'height': MODULE_HEIGHT,

    # Header
    'title_x': 5, 'title_y': 4, 'title_w': 40, 'title_h': 16,
    'bypass_x': 98, 'bypass_y': 3, 'bypass_w': 28, 'bypass_h': 18,

    # Separator
    'sep_y': 24,

    # Sliders (THR, MKP)
    'slider_y': 32, 'slider_h': 60, 'slider_w': 18,
    'thr_x': 8,
    'mkp_x': 34,

    # Labels
    'label_y': 96, 'label_h': 12,

    # Buttons row 1 (RATIO, ATK)
    'btn_row1_y': 32, 'btn_w': 28, 'btn_h': 18,
    'ratio_x': 64,
    'atk_x': 98,

    # Buttons row 2 (REL, SC)
    'btn_row2_y': 54,
    'rel_x': 64,
    'sc_x': 98,

    # GR meter
    'gr_x': 64, 'gr_y': 78, 'gr_w': 62, 'gr_h': 50,

    # Button labels
    'btn_label_y': 130, 'btn_label_h': 12,
}

CL = COMP_LAYOUT


class CompModule(QWidget):
    """SSL G-style bus compressor with flat absolute positioning."""

    RATIOS = ["2:1", "4:1", "10:1"]
    ATTACKS = ["0.1", "0.3", "1", "3", "10", "30"]
    RELEASES = ["0.1", "0.3", "0.6", "1.2", "A"]
    SC_HPFS = ["OFF", "60", "90", "150", "300"]

    comp_threshold_changed = pyqtSignal(float)
    comp_ratio_changed = pyqtSignal(int)
    comp_attack_changed = pyqtSignal(int)
    comp_release_changed = pyqtSignal(int)
    comp_makeup_changed = pyqtSignal(float)
    comp_sc_hpf_changed = pyqtSignal(int)
    comp_bypass_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("master_comp")

        self.bypassed = False
        self.ratio_idx = 1  # 4:1
        self.attack_idx = 4  # 10ms
        self.release_idx = 4  # Auto
        self.sc_idx = 0  # Off
        self.gr_value = 0

        self.setFixedSize(CL['width'], CL['height'])
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self._build_ui()
        self._update_style()

    def _build_ui(self):
        # Title
        self.title = QLabel("COMP", self)
        self.title.setFont(QFont(FONT_FAMILY, FONT_SIZES['tiny'], QFont.Bold))
        self.title.setStyleSheet(f"color: {get('accent_master')};")
        self.title.setGeometry(CL['title_x'], CL['title_y'], CL['title_w'], CL['title_h'])

        # Bypass button (CycleButton for drag support)
        self.bypass_btn = CycleButton(["ON", "BYP"], initial_index=0, parent=self)
        self.bypass_btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['micro']))
        self.bypass_btn.setGeometry(CL['bypass_x'], CL['bypass_y'], CL['bypass_w'], CL['bypass_h'])
        self.bypass_btn.index_changed.connect(self._on_bypass_changed)
        self._update_bypass_style()

        # Separator
        self.separator = QFrame(self)
        self.separator.setGeometry(4, CL['sep_y'], CL['width'] - 8, 1)
        self.separator.setStyleSheet(f"background-color: {get('accent_master_dim')};")

        # Threshold slider
        self.thr_slider = DragSlider(parent=self)
        self.thr_slider.setObjectName("master_comp_thr")
        self.thr_slider.setGeometry(CL['thr_x'], CL['slider_y'], CL['slider_w'], CL['slider_h'])
        self.thr_slider.setMinimum(0)
        self.thr_slider.setMaximum(400)  # -40 to 0 dB
        self.thr_slider.setValue(200)  # -20 dB
        self.thr_slider.setToolTip("Threshold (dB)")
        self.thr_slider.valueChanged.connect(self._on_thr_changed)

        thr_lbl = QLabel("THR", self)
        thr_lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        thr_lbl.setStyleSheet(f"color: {COLORS['text_dim']};")
        thr_lbl.setAlignment(Qt.AlignCenter)
        thr_lbl.setGeometry(CL['thr_x'] - 3, CL['label_y'], CL['slider_w'] + 6, CL['label_h'])

        # Makeup slider
        self.mkp_slider = DragSlider(parent=self)
        self.mkp_slider.setObjectName("master_comp_mkp")
        self.mkp_slider.setGeometry(CL['mkp_x'], CL['slider_y'], CL['slider_w'], CL['slider_h'])
        self.mkp_slider.setMinimum(0)
        self.mkp_slider.setMaximum(200)  # 0 to 20 dB
        self.mkp_slider.setValue(0)
        self.mkp_slider.setToolTip("Makeup gain (dB)")
        self.mkp_slider.valueChanged.connect(self._on_mkp_changed)

        mkp_lbl = QLabel("MKP", self)
        mkp_lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        mkp_lbl.setStyleSheet(f"color: {COLORS['text_dim']};")
        mkp_lbl.setAlignment(Qt.AlignCenter)
        mkp_lbl.setGeometry(CL['mkp_x'] - 3, CL['label_y'], CL['slider_w'] + 6, CL['label_h'])

        # Ratio button (CycleButton for drag support)
        self.ratio_btn = CycleButton(self.RATIOS, initial_index=self.ratio_idx, parent=self)
        self.ratio_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        self.ratio_btn.setGeometry(CL['ratio_x'], CL['btn_row1_y'], CL['btn_w'], CL['btn_h'])
        self.ratio_btn.setToolTip("Compression ratio")
        self.ratio_btn.index_changed.connect(self._on_ratio_changed)
        self.ratio_btn.setStyleSheet(small_btn_style())

        # Attack button (CycleButton for drag support)
        self.atk_btn = CycleButton(self.ATTACKS, initial_index=self.attack_idx, parent=self)
        self.atk_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        self.atk_btn.setGeometry(CL['atk_x'], CL['btn_row1_y'], CL['btn_w'], CL['btn_h'])
        self.atk_btn.setToolTip("Attack time (ms)")
        self.atk_btn.index_changed.connect(self._on_attack_changed)
        self.atk_btn.setStyleSheet(small_btn_style())

        # Release button (CycleButton for drag support)
        self.rel_btn = CycleButton(self.RELEASES, initial_index=self.release_idx, parent=self)
        self.rel_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        self.rel_btn.setGeometry(CL['rel_x'], CL['btn_row2_y'], CL['btn_w'], CL['btn_h'])
        self.rel_btn.setToolTip("Release time (s) / Auto")
        self.rel_btn.index_changed.connect(self._on_release_changed)
        self.rel_btn.setStyleSheet(small_btn_style())

        # SC HPF button (CycleButton for drag support)
        self.sc_btn = CycleButton(self.SC_HPFS, initial_index=self.sc_idx, parent=self)
        self.sc_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        self.sc_btn.setGeometry(CL['sc_x'], CL['btn_row2_y'], CL['btn_w'], CL['btn_h'])
        self.sc_btn.setToolTip("Sidechain HPF (Hz)")
        self.sc_btn.index_changed.connect(self._on_sc_changed)
        self.sc_btn.setStyleSheet(small_btn_style())

        # GR meter (custom painted)
        self.gr_meter = GRMeter(self)
        self.gr_meter.setGeometry(CL['gr_x'], CL['gr_y'], CL['gr_w'], CL['gr_h'])

        # Button labels row
        ratio_lbl = QLabel("RAT", self)
        ratio_lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        ratio_lbl.setStyleSheet(f"color: {COLORS['text_dim']};")
        ratio_lbl.setAlignment(Qt.AlignCenter)
        ratio_lbl.setGeometry(CL['ratio_x'] - 2, CL['btn_label_y'], CL['btn_w'] + 4, CL['btn_label_h'])

        atk_lbl = QLabel("ATK", self)
        atk_lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        atk_lbl.setStyleSheet(f"color: {COLORS['text_dim']};")
        atk_lbl.setAlignment(Qt.AlignCenter)
        atk_lbl.setGeometry(CL['atk_x'] - 2, CL['btn_label_y'], CL['btn_w'] + 4, CL['btn_label_h'])

    def _update_style(self):
        self.setStyleSheet(f"""
            QWidget#master_comp {{
                background-color: {COLORS['background']};
                border: 1px solid {get('accent_master_dim')};
                border-radius: 4px;
            }}
        """)

    def _on_bypass_changed(self, index):
        self.bypassed = (index == 1)  # 0=ON, 1=BYP
        self._update_bypass_style()
        self.comp_bypass_changed.emit(1 if self.bypassed else 0)

    def _update_bypass_style(self):
        self.bypass_btn.setStyleSheet(bypass_btn_style(self.bypassed))

    def _on_ratio_changed(self, index):
        self.ratio_idx = index
        self.comp_ratio_changed.emit(self.ratio_idx)

    def _on_attack_changed(self, index):
        self.attack_idx = index
        self.comp_attack_changed.emit(self.attack_idx)

    def _on_release_changed(self, index):
        self.release_idx = index
        self.comp_release_changed.emit(self.release_idx)

    def _on_sc_changed(self, index):
        self.sc_idx = index
        self.comp_sc_hpf_changed.emit(self.sc_idx)

    def _on_thr_changed(self, value):
        db = (value - 400) / 10.0  # -40 to 0 dB
        self.comp_threshold_changed.emit(db)

    def _on_mkp_changed(self, value):
        db = value / 10.0  # 0 to 20 dB
        self.comp_makeup_changed.emit(db)

    def set_gr(self, gr_db):
        """Set gain reduction meter value."""
        self.gr_meter.setValue(int(abs(gr_db) * 10))

    def get_state(self) -> dict:
        return {
            'bypass': self.bypassed,
            'threshold': self.thr_slider.value(),
            'makeup': self.mkp_slider.value(),
            'ratio': self.ratio_idx,
            'attack': self.attack_idx,
            'release': self.release_idx,
            'sc_hpf': self.sc_idx,
        }

    def set_state(self, state: dict):
        if 'bypass' in state:
            self.bypassed = state['bypass']
            self.bypass_btn.set_index(1 if self.bypassed else 0)
            self._update_bypass_style()
            self.comp_bypass_changed.emit(1 if self.bypassed else 0)
        if 'threshold' in state:
            self.thr_slider.setValue(state['threshold'])
        if 'makeup' in state:
            self.mkp_slider.setValue(state['makeup'])
        if 'ratio' in state:
            self.ratio_btn.set_index(state['ratio'])
        if 'attack' in state:
            self.atk_btn.set_index(state['attack'])
        if 'release' in state:
            self.rel_btn.set_index(state['release'])
        if 'sc_hpf' in state:
            self.sc_btn.set_index(state['sc_hpf'])


class GRMeter(QWidget):
    """Compact gain reduction meter."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.gr_value = 0  # 0-200 (0-20dB)

    def setValue(self, value):
        self.gr_value = max(0, min(200, value))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor(COLORS['background_dark']))

        # Border
        painter.setPen(QColor(COLORS['border']))
        painter.drawRect(0, 0, w - 1, h - 1)

        # GR bar (fills from top)
        if self.gr_value > 0:
            bar_height = int((self.gr_value / 200.0) * (h - 4))
            gradient = QLinearGradient(2, 2, 2, 2 + bar_height)
            gradient.setColorAt(0.0, QColor('#ff8844'))
            gradient.setColorAt(1.0, QColor('#ff6622'))
            painter.fillRect(2, 2, w - 4, bar_height, gradient)

        # GR label
        painter.setPen(QColor(COLORS['text_dim']))
        painter.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        painter.drawText(0, 0, w, h, Qt.AlignCenter, "GR")


# =============================================================================
# LIMITER MODULE - Flat Layout
# =============================================================================

LIM_LAYOUT = {
    'width': 55,
    'height': MODULE_HEIGHT,

    # Header
    'title_x': 5, 'title_y': 4, 'title_w': 24, 'title_h': 16,
    'bypass_x': 24, 'bypass_y': 3, 'bypass_w': 28, 'bypass_h': 18,

    # Separator
    'sep_y': 24,

    # Ceiling slider
    'slider_x': 18, 'slider_y': 32, 'slider_h': 80, 'slider_w': 18,

    # Label
    'label_y': 116, 'label_h': 12,

    # dB readout
    'db_y': 130, 'db_h': 14,
}

LL = LIM_LAYOUT


class LimiterModule(QWidget):
    """Brickwall limiter with flat absolute positioning."""

    limiter_ceiling_changed = pyqtSignal(float)
    limiter_bypass_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("master_lim")

        self.bypassed = False
        self.ceiling_db = -0.1

        self.setFixedSize(LL['width'], LL['height'])
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self._build_ui()
        self._update_style()

    def _build_ui(self):
        # Title
        self.title = QLabel("LIM", self)
        self.title.setFont(QFont(FONT_FAMILY, FONT_SIZES['tiny'], QFont.Bold))
        self.title.setStyleSheet(f"color: {get('accent_master')};")
        self.title.setGeometry(LL['title_x'], LL['title_y'], LL['title_w'], LL['title_h'])

        # Bypass button (CycleButton for drag support)
        self.bypass_btn = CycleButton(["ON", "BYP"], initial_index=0, parent=self)
        self.bypass_btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['micro']))
        self.bypass_btn.setGeometry(LL['bypass_x'], LL['bypass_y'], LL['bypass_w'], LL['bypass_h'])
        self.bypass_btn.index_changed.connect(self._on_bypass_changed)
        self._update_bypass_style()

        # Separator
        self.separator = QFrame(self)
        self.separator.setGeometry(4, LL['sep_y'], LL['width'] - 8, 1)
        self.separator.setStyleSheet(f"background-color: {get('accent_master_dim')};")

        # Ceiling slider
        self.ceil_slider = DragSlider(parent=self)
        self.ceil_slider.setObjectName("master_lim_ceil")
        self.ceil_slider.setGeometry(LL['slider_x'], LL['slider_y'], LL['slider_w'], LL['slider_h'])
        self.ceil_slider.setMinimum(0)
        self.ceil_slider.setMaximum(60)  # -6 to 0 dB
        self.ceil_slider.setValue(59)  # -0.1 dB
        self.ceil_slider.setToolTip("Ceiling (dB)")
        self.ceil_slider.valueChanged.connect(self._on_ceil_changed)

        ceil_lbl = QLabel("CEIL", self)
        ceil_lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        ceil_lbl.setStyleSheet(f"color: {COLORS['text_dim']};")
        ceil_lbl.setAlignment(Qt.AlignCenter)
        ceil_lbl.setGeometry(2, LL['label_y'], LL['width'] - 4, LL['label_h'])

        # dB readout
        self.db_label = QLabel("-0.1", self)
        self.db_label.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        self.db_label.setStyleSheet(f"color: {COLORS['text']};")
        self.db_label.setAlignment(Qt.AlignCenter)
        self.db_label.setGeometry(2, LL['db_y'], LL['width'] - 4, LL['db_h'])

    def _update_style(self):
        self.setStyleSheet(f"""
            QWidget#master_lim {{
                background-color: {COLORS['background']};
                border: 1px solid {get('accent_master_dim')};
                border-radius: 4px;
            }}
        """)

    def _on_bypass_changed(self, index):
        self.bypassed = (index == 1)  # 0=ON, 1=BYP
        self._update_bypass_style()
        self.limiter_bypass_changed.emit(1 if self.bypassed else 0)

    def _update_bypass_style(self):
        self.bypass_btn.setStyleSheet(bypass_btn_style(self.bypassed))

    def _on_ceil_changed(self, value):
        self.ceiling_db = (value - 60) / 10.0  # -6 to 0 dB
        self.db_label.setText(f"{self.ceiling_db:.1f}")
        self.limiter_ceiling_changed.emit(self.ceiling_db)

    def get_state(self) -> dict:
        return {
            'bypass': self.bypassed,
            'ceiling': self.ceil_slider.value(),
        }

    def set_state(self, state: dict):
        if 'bypass' in state:
            self.bypassed = state['bypass']
            self.bypass_btn.set_index(1 if self.bypassed else 0)
            self._update_bypass_style()
            self.limiter_bypass_changed.emit(1 if self.bypassed else 0)
        if 'ceiling' in state:
            self.ceil_slider.setValue(state['ceiling'])


# =============================================================================
# OUTPUT MODULE - Flat Layout (Volume + Meters)
# =============================================================================

OUT_LAYOUT = {
    'width': 60,
    'height': MODULE_HEIGHT,

    # Header
    'title_x': 5, 'title_y': 4, 'title_w': 30, 'title_h': 16,
    'mode_x': 32, 'mode_y': 3, 'mode_w': 24, 'mode_h': 18,

    # Separator
    'sep_y': 24,

    # Volume slider
    'vol_x': 6, 'vol_y': 32, 'vol_h': 100, 'vol_w': 18,

    # Meters
    'meter_x': 32, 'meter_y': 32, 'meter_w': 22, 'meter_h': 100,

    # Label
    'label_y': 136, 'label_h': 12,
}

OL = OUT_LAYOUT


class OutputModule(QWidget):
    """Master output with volume fader and level meters."""

    master_volume_changed = pyqtSignal(float)
    meter_mode_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("master_out")

        self.meter_mode = 0  # 0=PRE, 1=POST

        self.setFixedSize(OL['width'], OL['height'])
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self._build_ui()
        self._update_style()

    def _build_ui(self):
        # Title
        self.title = QLabel("OUT", self)
        self.title.setFont(QFont(FONT_FAMILY, FONT_SIZES['tiny'], QFont.Bold))
        self.title.setStyleSheet(f"color: {get('accent_master')};")
        self.title.setGeometry(OL['title_x'], OL['title_y'], OL['title_w'], OL['title_h'])

        # PRE/POST mode button (CycleButton for drag support)
        self.mode_btn = CycleButton(["PRE", "POST"], initial_index=0, parent=self)
        self.mode_btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['micro']))
        self.mode_btn.setGeometry(OL['mode_x'], OL['mode_y'], OL['mode_w'], OL['mode_h'])
        self.mode_btn.setToolTip("Meter mode: PRE/POST fader")
        self.mode_btn.index_changed.connect(self._on_mode_changed)
        self.mode_btn.setStyleSheet(small_btn_style())

        # Separator
        self.separator = QFrame(self)
        self.separator.setGeometry(4, OL['sep_y'], OL['width'] - 8, 1)
        self.separator.setStyleSheet(f"background-color: {get('accent_master_dim')};")

        # Volume slider
        self.vol_slider = DragSlider(parent=self)
        self.vol_slider.setObjectName("master_volume")
        self.vol_slider.setGeometry(OL['vol_x'], OL['vol_y'], OL['vol_w'], OL['vol_h'])
        self.vol_slider.setMinimum(0)
        self.vol_slider.setMaximum(1000)
        self.vol_slider.setValue(800)  # ~0 dB
        self.vol_slider.setToolTip("Master volume")
        self.vol_slider.valueChanged.connect(self._on_vol_changed)

        vol_lbl = QLabel("VOL", self)
        vol_lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        vol_lbl.setStyleSheet(f"color: {COLORS['text_dim']};")
        vol_lbl.setAlignment(Qt.AlignCenter)
        vol_lbl.setGeometry(OL['vol_x'] - 2, OL['label_y'], OL['vol_w'] + 4, OL['label_h'])

        # Level meter
        self.meter = LevelMeter(self)
        self.meter.setGeometry(OL['meter_x'], OL['meter_y'], OL['meter_w'], OL['meter_h'])

    def _update_style(self):
        self.setStyleSheet(f"""
            QWidget#master_out {{
                background-color: {COLORS['background']};
                border: 1px solid {get('accent_master_dim')};
                border-radius: 4px;
            }}
        """)

    def _on_mode_changed(self, index):
        self.meter_mode = index  # 0=PRE, 1=POST
        self.meter_mode_changed.emit(self.meter_mode)

    def _on_vol_changed(self, value):
        # Convert to dB-ish scale
        self.master_volume_changed.emit(value / 1000.0)

    def set_levels(self, left, right, peak_left=None, peak_right=None):
        self.meter.set_levels(left, right, peak_left, peak_right)

    def get_volume(self):
        """Get current master volume (0.0 to 1.0)."""
        return self.vol_slider.value() / 1000.0

    def set_volume(self, value):
        """Set master volume (0.0 to 1.0)."""
        self.vol_slider.setValue(int(value * 1000))

    def get_state(self) -> dict:
        return {
            'volume': self.vol_slider.value(),
            'meter_mode': self.meter_mode,
        }

    def set_state(self, state: dict):
        if 'volume' in state:
            self.vol_slider.setValue(int(state['volume']))
        if 'meter_mode' in state:
            self.mode_btn.set_index(state['meter_mode'])


class LevelMeter(QWidget):
    """Compact stereo level meter."""

    PEAK_HOLD_MS = 1500
    CLIP_HOLD_MS = 2000

    def __init__(self, parent=None):
        super().__init__(parent)
        self.level_l = 0.0
        self.level_r = 0.0
        self.peak_l = 0.0
        self.peak_r = 0.0
        self.clip_l = False
        self.clip_r = False

        self.peak_timer = QTimer(self)
        self.peak_timer.timeout.connect(self._decay_peaks)
        self.peak_timer.start(50)

        self.clip_timer_l = QTimer(self)
        self.clip_timer_l.setSingleShot(True)
        self.clip_timer_l.timeout.connect(lambda: self._reset_clip('l'))

        self.clip_timer_r = QTimer(self)
        self.clip_timer_r.setSingleShot(True)
        self.clip_timer_r.timeout.connect(lambda: self._reset_clip('r'))

        self.peak_l_time = 0
        self.peak_r_time = 0
        self._tick = 0

    def set_levels(self, left, right, peak_left=None, peak_right=None):
        self.level_l = max(0.0, min(1.0, left))
        self.level_r = max(0.0, min(1.0, right))

        if peak_left is not None and peak_left > self.peak_l:
            self.peak_l = min(1.0, peak_left)
            self.peak_l_time = self._tick
        elif left > self.peak_l:
            self.peak_l = min(1.0, left)
            self.peak_l_time = self._tick

        if peak_right is not None and peak_right > self.peak_r:
            self.peak_r = min(1.0, peak_right)
            self.peak_r_time = self._tick
        elif right > self.peak_r:
            self.peak_r = min(1.0, right)
            self.peak_r_time = self._tick

        if left > 0.99:
            self.clip_l = True
            self.clip_timer_l.start(self.CLIP_HOLD_MS)
        if right > 0.99:
            self.clip_r = True
            self.clip_timer_r.start(self.CLIP_HOLD_MS)

        self.update()

    def _decay_peaks(self):
        self._tick += 1
        hold_ticks = self.PEAK_HOLD_MS // 50

        if self._tick - self.peak_l_time > hold_ticks:
            self.peak_l = max(self.level_l, self.peak_l * 0.95)
        if self._tick - self.peak_r_time > hold_ticks:
            self.peak_r = max(self.level_r, self.peak_r * 0.95)

        self.update()

    def _reset_clip(self, channel):
        if channel == 'l':
            self.clip_l = False
        else:
            self.clip_r = False
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        meter_w = 8
        gap = 2
        clip_h = 8

        left_x = 2
        right_x = left_x + meter_w + gap
        meter_y = clip_h + 4
        meter_h = h - meter_y - 2

        # Backgrounds
        bg = QColor(COLORS['background_dark'])
        painter.fillRect(left_x, meter_y, meter_w, meter_h, bg)
        painter.fillRect(right_x, meter_y, meter_w, meter_h, bg)

        # Level bars
        self._draw_bar(painter, left_x, meter_y, meter_w, meter_h, self.level_l)
        self._draw_bar(painter, right_x, meter_y, meter_w, meter_h, self.level_r)

        # Peak indicators
        peak_color = QColor(COLORS['text_bright'])
        if self.peak_l > 0.01:
            peak_y = meter_y + meter_h - int(self.peak_l * meter_h)
            painter.fillRect(left_x, peak_y, meter_w, 2, peak_color)
        if self.peak_r > 0.01:
            peak_y = meter_y + meter_h - int(self.peak_r * meter_h)
            painter.fillRect(right_x, peak_y, meter_w, 2, peak_color)

        # Clip indicators
        clip_off = QColor(COLORS['border'])
        clip_on = QColor('#ff2222')
        painter.fillRect(left_x, 2, meter_w, clip_h, clip_on if self.clip_l else clip_off)
        painter.fillRect(right_x, 2, meter_w, clip_h, clip_on if self.clip_r else clip_off)

    def _draw_bar(self, painter, x, y, w, h, level):
        if level < 0.001:
            return
        bar_h = int(level * h)
        bar_y = y + h - bar_h

        gradient = QLinearGradient(x, y + h, x, y)
        gradient.setColorAt(0.0, QColor('#22aa22'))
        gradient.setColorAt(0.6, QColor('#22aa22'))
        gradient.setColorAt(0.75, QColor('#aaaa22'))
        gradient.setColorAt(0.9, QColor('#aa2222'))
        gradient.setColorAt(1.0, QColor('#ff2222'))

        painter.fillRect(x, bar_y, w, bar_h, gradient)


# =============================================================================
# MASTER CHAIN - Container for all modules
# =============================================================================

class MasterChain(QWidget):
    """
    Unified master chain: Heat → Filter → EQ → Comp → Limiter → Output
    All modules use flat absolute positioning for visual consistency.
    """

    # Forward all signals
    master_volume_changed = pyqtSignal(float)
    meter_mode_changed = pyqtSignal(int)
    limiter_ceiling_changed = pyqtSignal(float)
    limiter_bypass_changed = pyqtSignal(int)
    eq_lo_changed = pyqtSignal(float)
    eq_mid_changed = pyqtSignal(float)
    eq_hi_changed = pyqtSignal(float)
    eq_lo_kill_changed = pyqtSignal(int)
    eq_mid_kill_changed = pyqtSignal(int)
    eq_hi_kill_changed = pyqtSignal(int)
    eq_locut_changed = pyqtSignal(int)
    eq_bypass_changed = pyqtSignal(int)
    comp_threshold_changed = pyqtSignal(float)
    comp_ratio_changed = pyqtSignal(int)
    comp_attack_changed = pyqtSignal(int)
    comp_release_changed = pyqtSignal(int)
    comp_makeup_changed = pyqtSignal(float)
    comp_sc_hpf_changed = pyqtSignal(int)
    comp_bypass_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("master_chain")
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.osc_bridge = None

        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)

        # Signal flow order: Heat → Filter → EQ → Comp → Limiter → Output
        self.heat = HeatModule()
        layout.addWidget(self.heat)

        self.filter = FilterModule()
        layout.addWidget(self.filter)

        self.eq = EQModule()
        layout.addWidget(self.eq)

        self.comp = CompModule()
        layout.addWidget(self.comp)

        self.limiter = LimiterModule()
        layout.addWidget(self.limiter)

        self.output = OutputModule()
        layout.addWidget(self.output)

        layout.addStretch()

    def _connect_signals(self):
        # EQ signals
        self.eq.eq_lo_changed.connect(self.eq_lo_changed.emit)
        self.eq.eq_mid_changed.connect(self.eq_mid_changed.emit)
        self.eq.eq_hi_changed.connect(self.eq_hi_changed.emit)
        self.eq.eq_lo_kill_changed.connect(self.eq_lo_kill_changed.emit)
        self.eq.eq_mid_kill_changed.connect(self.eq_mid_kill_changed.emit)
        self.eq.eq_hi_kill_changed.connect(self.eq_hi_kill_changed.emit)
        self.eq.eq_locut_changed.connect(self.eq_locut_changed.emit)
        self.eq.eq_bypass_changed.connect(self.eq_bypass_changed.emit)

        # Comp signals
        self.comp.comp_threshold_changed.connect(self.comp_threshold_changed.emit)
        self.comp.comp_ratio_changed.connect(self.comp_ratio_changed.emit)
        self.comp.comp_attack_changed.connect(self.comp_attack_changed.emit)
        self.comp.comp_release_changed.connect(self.comp_release_changed.emit)
        self.comp.comp_makeup_changed.connect(self.comp_makeup_changed.emit)
        self.comp.comp_sc_hpf_changed.connect(self.comp_sc_hpf_changed.emit)
        self.comp.comp_bypass_changed.connect(self.comp_bypass_changed.emit)

        # Limiter signals
        self.limiter.limiter_ceiling_changed.connect(self.limiter_ceiling_changed.emit)
        self.limiter.limiter_bypass_changed.connect(self.limiter_bypass_changed.emit)

        # Output signals
        self.output.master_volume_changed.connect(self.master_volume_changed.emit)
        self.output.meter_mode_changed.connect(self.meter_mode_changed.emit)

    def set_osc_bridge(self, osc_bridge):
        self.osc_bridge = osc_bridge
        self.heat.set_osc_bridge(osc_bridge)
        self.filter.set_osc_bridge(osc_bridge)

    def sync_state(self):
        self.heat.sync_state()
        self.filter.sync_state()

    def set_levels(self, left, right, peak_left=None, peak_right=None):
        self.output.set_levels(left, right, peak_left, peak_right)

    def set_comp_gr(self, gr_db):
        self.comp.set_gr(gr_db)

    def get_volume(self):
        return self.output.get_volume()

    def set_volume(self, value):
        self.output.set_volume(value)

    def get_state(self) -> dict:
        """Get state in flat prefixed format matching MasterState schema."""
        heat = self.heat.get_state()
        flt = self.filter.get_state()
        eq = self.eq.get_state()
        comp = self.comp.get_state()
        lim = self.limiter.get_state()
        out = self.output.get_state()

        return {
            # Output
            'volume': out.get('volume', 800) / 1000.0,  # Convert 0-1000 to 0-1
            'meter_mode': out.get('meter_mode', 0),
            # Heat
            'heat_bypass': 1 if heat.get('bypass', True) else 0,
            'heat_circuit': heat.get('circuit', 0),
            'heat_drive': heat.get('drive', 0),
            'heat_mix': heat.get('mix', 200),
            # Filter
            'filter_bypass': 1 if flt.get('bypass', True) else 0,
            'filter_f1': flt.get('f1', 100),
            'filter_r1': flt.get('r1', 0),
            'filter_f1_mode': flt.get('f1_mode', 0),
            'filter_f2': flt.get('f2', 100),
            'filter_r2': flt.get('r2', 0),
            'filter_f2_mode': flt.get('f2_mode', 2),
            'filter_routing': flt.get('routing', 0),
            'filter_mix': flt.get('mix', 200),
            # Sync (now part of filter module)
            'sync_f1': flt.get('f1_sync', 'FREE'),
            'sync_f2': flt.get('f2_sync', 'FREE'),
            'sync_amt': flt.get('amt', 0),
            # EQ
            'eq_bypass': 1 if eq.get('bypass', False) else 0,
            'eq_lo': eq.get('lo', 120),
            'eq_mid': eq.get('mid', 120),
            'eq_hi': eq.get('hi', 120),
            'eq_lo_kill': eq.get('lo_kill', 0),
            'eq_mid_kill': eq.get('mid_kill', 0),
            'eq_hi_kill': eq.get('hi_kill', 0),
            'eq_locut': eq.get('locut', 0),
            # Compressor
            'comp_bypass': 1 if comp.get('bypass', False) else 0,
            'comp_threshold': comp.get('threshold', 100),
            'comp_makeup': comp.get('makeup', 0),
            'comp_ratio': comp.get('ratio', 1),
            'comp_attack': comp.get('attack', 4),
            'comp_release': comp.get('release', 4),
            'comp_sc': comp.get('sc_hpf', 0),
            # Limiter
            'limiter_bypass': 1 if lim.get('bypass', False) else 0,
            'limiter_ceiling': lim.get('ceiling', 590),
        }

    def set_state(self, state: dict):
        """Set state from flat prefixed format (MasterState schema)."""
        # Support both nested (legacy) and flat (new) formats
        if 'heat' in state:
            # Legacy nested format
            self.heat.set_state(state['heat'])
            if 'filter' in state:
                self.filter.set_state(state['filter'])
            if 'sync' in state:
                # Legacy: sync was separate, now merged into filter
                self.filter.set_state(state['sync'])
            if 'eq' in state:
                self.eq.set_state(state['eq'])
            if 'comp' in state:
                self.comp.set_state(state['comp'])
            if 'limiter' in state:
                self.limiter.set_state(state['limiter'])
            if 'output' in state:
                self.output.set_state(state['output'])
        else:
            # New flat prefixed format
            # Heat
            self.heat.set_state({
                'bypass': state.get('heat_bypass', 1) == 1,
                'circuit': state.get('heat_circuit', 0),
                'drive': state.get('heat_drive', 0),
                'mix': state.get('heat_mix', 200),
            })
            # Filter (includes sync)
            self.filter.set_state({
                'bypass': state.get('filter_bypass', 1) == 1,
                'f1': state.get('filter_f1', 100),
                'r1': state.get('filter_r1', 0),
                'f1_mode': state.get('filter_f1_mode', 0),
                'f2': state.get('filter_f2', 100),
                'r2': state.get('filter_r2', 0),
                'f2_mode': state.get('filter_f2_mode', 2),
                'routing': state.get('filter_routing', 0),
                'mix': state.get('filter_mix', 200),
                'f1_sync': state.get('sync_f1', 'FREE'),
                'f2_sync': state.get('sync_f2', 'FREE'),
                'amt': state.get('sync_amt', 0),
            })
            # EQ
            self.eq.set_state({
                'bypass': state.get('eq_bypass', 0) == 1,
                'lo': state.get('eq_lo', 120),
                'mid': state.get('eq_mid', 120),
                'hi': state.get('eq_hi', 120),
                'lo_kill': state.get('eq_lo_kill', 0),
                'mid_kill': state.get('eq_mid_kill', 0),
                'hi_kill': state.get('eq_hi_kill', 0),
                'locut': state.get('eq_locut', 0),
            })
            # Compressor
            self.comp.set_state({
                'bypass': state.get('comp_bypass', 0) == 1,
                'threshold': state.get('comp_threshold', 100),
                'makeup': state.get('comp_makeup', 0),
                'ratio': state.get('comp_ratio', 1),
                'attack': state.get('comp_attack', 4),
                'release': state.get('comp_release', 4),
                'sc_hpf': state.get('comp_sc', 0),
            })
            # Limiter
            self.limiter.set_state({
                'bypass': state.get('limiter_bypass', 0) == 1,
                'ceiling': state.get('limiter_ceiling', 590),
            })
            # Output
            self.output.set_state({
                'volume': int(state.get('volume', 0.8) * 1000),  # Convert 0-1 to 0-1000
                'meter_mode': state.get('meter_mode', 0),
            })

    # Legacy compatibility - forward to embedded master_section-like interface
    @property
    def master_section(self):
        """Legacy compatibility: return self since we now contain all functionality."""
        return self
