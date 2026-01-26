"""
Master Chain Component - Phase 2
Unified master section: Heat → Filter → EQ → Comp → Limiter → Output

Heat and Filter are master inserts (from old InlineFXStrip).
EQ, Comp, Limiter, Output come from MasterSection.
"""

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame, QPushButton
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from .theme import COLORS, MONO_FONT, FONT_FAMILY, FONT_SIZES, get
from .widgets import MiniKnob, DragSlider
from .master_section import MasterSection
from src.config import OSC_PATHS


# =============================================================================
# HEAT INSERT MODULE
# =============================================================================

class HeatInsert(QFrame):
    """Compact Heat saturation module for master chain."""

    CIRCUITS = ["CLN", "TAPE", "TUBE", "CRSH"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("master_heat")
        self.circuit_index = 0
        self.bypassed = True  # Start bypassed
        self.osc_bridge = None
        self._build_ui()

    def _build_ui(self):
        """Build Heat insert UI."""
        self.setStyleSheet(f"""
            QFrame#master_heat {{
                background-color: {COLORS['background']};
                border: 1px solid {get('accent_master_dim')};
                border-radius: 4px;
            }}
        """)
        self.setFixedWidth(80)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(3)

        # Header: HEAT + bypass
        header = QHBoxLayout()
        header.setSpacing(2)

        title = QLabel("HEAT")
        title.setFont(QFont(FONT_FAMILY, FONT_SIZES['tiny'], QFont.Bold))
        title.setStyleSheet(f"color: {get('accent_master')}; border: none;")
        header.addWidget(title)
        header.addStretch()

        self.bypass_btn = QPushButton("BYP")
        self.bypass_btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['micro']))
        self.bypass_btn.setFixedSize(28, 16)
        self.bypass_btn.clicked.connect(self._toggle_bypass)
        self._update_bypass_style()
        header.addWidget(self.bypass_btn)

        layout.addLayout(header)

        # Knobs row
        knobs = QHBoxLayout()
        knobs.setSpacing(4)

        # Drive
        drv_col = QVBoxLayout()
        drv_col.setSpacing(1)
        self.drive_knob = MiniKnob()
        self.drive_knob.setObjectName("master_heat_drive")
        self.drive_knob.setFixedSize(22, 22)
        self.drive_knob.setValue(0)
        self.drive_knob.setToolTip("Drive amount")
        self.drive_knob.valueChanged.connect(self._on_drive_changed)
        drv_col.addWidget(self.drive_knob, alignment=Qt.AlignCenter)
        drv_lbl = QLabel("DRV")
        drv_lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        drv_lbl.setStyleSheet(f"color: {COLORS['text_dim']}; border: none;")
        drv_lbl.setAlignment(Qt.AlignCenter)
        drv_col.addWidget(drv_lbl)
        knobs.addLayout(drv_col)

        # Mix
        mix_col = QVBoxLayout()
        mix_col.setSpacing(1)
        self.mix_knob = MiniKnob()
        self.mix_knob.setObjectName("master_heat_mix")
        self.mix_knob.setFixedSize(22, 22)
        self.mix_knob.setValue(100)  # 50%
        self.mix_knob.setToolTip("Dry/Wet mix")
        self.mix_knob.valueChanged.connect(self._on_mix_changed)
        mix_col.addWidget(self.mix_knob, alignment=Qt.AlignCenter)
        mix_lbl = QLabel("MIX")
        mix_lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        mix_lbl.setStyleSheet(f"color: {COLORS['text_dim']}; border: none;")
        mix_lbl.setAlignment(Qt.AlignCenter)
        mix_col.addWidget(mix_lbl)
        knobs.addLayout(mix_col)

        layout.addLayout(knobs)

        # Circuit selector
        self.circuit_btn = QPushButton(self.CIRCUITS[0])
        self.circuit_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        self.circuit_btn.setFixedHeight(18)
        self.circuit_btn.setToolTip("Saturation circuit type")
        self.circuit_btn.clicked.connect(self._cycle_circuit)
        self.circuit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['background_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 2px;
            }}
            QPushButton:hover {{
                border-color: {COLORS['text_dim']};
            }}
        """)
        layout.addWidget(self.circuit_btn)

        layout.addStretch()

    def _toggle_bypass(self):
        """Toggle bypass state."""
        self.bypassed = not self.bypassed
        self._update_bypass_style()
        self._send_osc(OSC_PATHS['heat_bypass'], 1 if self.bypassed else 0)

    def _update_bypass_style(self):
        """Update bypass button appearance."""
        if self.bypassed:
            self.bypass_btn.setText("BYP")
            self.bypass_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['warning']};
                    color: {COLORS['warning_text']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 2px;
                }}
            """)
        else:
            self.bypass_btn.setText("ON")
            self.bypass_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['enabled']};
                    color: {COLORS['enabled_text']};
                    border: 1px solid {COLORS['border_active']};
                    border-radius: 2px;
                }}
            """)

    def _cycle_circuit(self):
        """Cycle through circuit types."""
        self.circuit_index = (self.circuit_index + 1) % len(self.CIRCUITS)
        self.circuit_btn.setText(self.CIRCUITS[self.circuit_index])
        self._send_osc(OSC_PATHS['heat_circuit'], self.circuit_index)

    def _on_drive_changed(self, value):
        """Handle drive knob change."""
        self._send_osc(OSC_PATHS['heat_drive'], value / 200.0)

    def _on_mix_changed(self, value):
        """Handle mix knob change."""
        self._send_osc(OSC_PATHS['heat_mix'], value / 200.0)

    def set_osc_bridge(self, osc_bridge):
        """Set OSC bridge."""
        self.osc_bridge = osc_bridge

    def _send_osc(self, path, value):
        """Send OSC message if connected."""
        if self.osc_bridge and self.osc_bridge.client:
            self.osc_bridge.client.send_message(path, [value])

    def sync_state(self):
        """Sync all state to SC."""
        self._send_osc(OSC_PATHS['heat_bypass'], 1 if self.bypassed else 0)
        self._send_osc(OSC_PATHS['heat_circuit'], self.circuit_index)
        self._send_osc(OSC_PATHS['heat_drive'], self.drive_knob.value() / 200.0)
        self._send_osc(OSC_PATHS['heat_mix'], self.mix_knob.value() / 200.0)

    def get_state(self) -> dict:
        """Get state for preset."""
        return {
            'bypass': self.bypassed,
            'circuit': self.circuit_index,
            'drive': self.drive_knob.value(),
            'mix': self.mix_knob.value(),
        }

    def set_state(self, state: dict):
        """Restore state from preset."""
        if 'bypass' in state and state['bypass'] != self.bypassed:
            self._toggle_bypass()
        if 'circuit' in state:
            self.circuit_index = state['circuit']
            self.circuit_btn.setText(self.CIRCUITS[self.circuit_index])
            self._send_osc(OSC_PATHS['heat_circuit'], self.circuit_index)
        if 'drive' in state:
            self.drive_knob.setValue(state['drive'])
        if 'mix' in state:
            self.mix_knob.setValue(state['mix'])


# =============================================================================
# FILTER INSERT MODULE
# =============================================================================

class FilterInsert(QFrame):
    """Compact dual filter module for master chain."""

    MODES = ["LP", "BP", "HP"]
    ROUTINGS = ["SER", "PAR"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("master_filter")
        self.f1_mode = 0  # LP
        self.f2_mode = 0  # LP
        self.routing = 0  # Serial
        self.bypassed = True  # Start bypassed
        self.osc_bridge = None
        self._build_ui()

    def _build_ui(self):
        """Build Filter insert UI."""
        self.setStyleSheet(f"""
            QFrame#master_filter {{
                background-color: {COLORS['background']};
                border: 1px solid {get('accent_master_dim')};
                border-radius: 4px;
            }}
        """)
        self.setFixedWidth(120)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(3)

        # Header: FILT + bypass
        header = QHBoxLayout()
        header.setSpacing(2)

        title = QLabel("FILT")
        title.setFont(QFont(FONT_FAMILY, FONT_SIZES['tiny'], QFont.Bold))
        title.setStyleSheet(f"color: {get('accent_master')}; border: none;")
        header.addWidget(title)
        header.addStretch()

        self.bypass_btn = QPushButton("BYP")
        self.bypass_btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['micro']))
        self.bypass_btn.setFixedSize(28, 16)
        self.bypass_btn.clicked.connect(self._toggle_bypass)
        self._update_bypass_style()
        header.addWidget(self.bypass_btn)

        layout.addLayout(header)

        # Knobs row: F1 R1 | F2 R2
        knobs = QHBoxLayout()
        knobs.setSpacing(2)

        # F1
        f1_col = QVBoxLayout()
        f1_col.setSpacing(1)
        self.f1_knob = MiniKnob()
        self.f1_knob.setObjectName("master_filt_freq1")
        self.f1_knob.setFixedSize(20, 20)
        self.f1_knob.setValue(120)  # 60%
        self.f1_knob.setToolTip("Filter 1 frequency")
        self.f1_knob.valueChanged.connect(self._on_f1_changed)
        f1_col.addWidget(self.f1_knob, alignment=Qt.AlignCenter)
        self.f1_mode_btn = QPushButton("LP")
        self.f1_mode_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        self.f1_mode_btn.setFixedSize(20, 14)
        self.f1_mode_btn.clicked.connect(self._cycle_f1_mode)
        self._update_mode_btn_style(self.f1_mode_btn)
        f1_col.addWidget(self.f1_mode_btn, alignment=Qt.AlignCenter)
        knobs.addLayout(f1_col)

        # R1
        r1_col = QVBoxLayout()
        r1_col.setSpacing(1)
        self.r1_knob = MiniKnob()
        self.r1_knob.setObjectName("master_filt_reso1")
        self.r1_knob.setFixedSize(20, 20)
        self.r1_knob.setValue(60)  # 30%
        self.r1_knob.setToolTip("Filter 1 resonance")
        self.r1_knob.valueChanged.connect(self._on_r1_changed)
        r1_col.addWidget(self.r1_knob, alignment=Qt.AlignCenter)
        r1_lbl = QLabel("R1")
        r1_lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        r1_lbl.setStyleSheet(f"color: {COLORS['text_dim']}; border: none;")
        r1_lbl.setAlignment(Qt.AlignCenter)
        r1_col.addWidget(r1_lbl)
        knobs.addLayout(r1_col)

        # F2
        f2_col = QVBoxLayout()
        f2_col.setSpacing(1)
        self.f2_knob = MiniKnob()
        self.f2_knob.setObjectName("master_filt_freq2")
        self.f2_knob.setFixedSize(20, 20)
        self.f2_knob.setValue(120)  # 60%
        self.f2_knob.setToolTip("Filter 2 frequency")
        self.f2_knob.valueChanged.connect(self._on_f2_changed)
        f2_col.addWidget(self.f2_knob, alignment=Qt.AlignCenter)
        self.f2_mode_btn = QPushButton("LP")
        self.f2_mode_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        self.f2_mode_btn.setFixedSize(20, 14)
        self.f2_mode_btn.clicked.connect(self._cycle_f2_mode)
        self._update_mode_btn_style(self.f2_mode_btn)
        f2_col.addWidget(self.f2_mode_btn, alignment=Qt.AlignCenter)
        knobs.addLayout(f2_col)

        # R2
        r2_col = QVBoxLayout()
        r2_col.setSpacing(1)
        self.r2_knob = MiniKnob()
        self.r2_knob.setObjectName("master_filt_reso2")
        self.r2_knob.setFixedSize(20, 20)
        self.r2_knob.setValue(60)  # 30%
        self.r2_knob.setToolTip("Filter 2 resonance")
        self.r2_knob.valueChanged.connect(self._on_r2_changed)
        r2_col.addWidget(self.r2_knob, alignment=Qt.AlignCenter)
        r2_lbl = QLabel("R2")
        r2_lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        r2_lbl.setStyleSheet(f"color: {COLORS['text_dim']}; border: none;")
        r2_lbl.setAlignment(Qt.AlignCenter)
        r2_col.addWidget(r2_lbl)
        knobs.addLayout(r2_col)

        layout.addLayout(knobs)

        # Bottom: routing button
        self.routing_btn = QPushButton("SER")
        self.routing_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        self.routing_btn.setFixedHeight(16)
        self.routing_btn.setToolTip("Serial/Parallel routing")
        self.routing_btn.clicked.connect(self._toggle_routing)
        self.routing_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['background_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 2px;
            }}
        """)
        layout.addWidget(self.routing_btn)

        layout.addStretch()

    def _update_mode_btn_style(self, btn):
        """Update filter mode button style."""
        btn.setStyleSheet(f"""
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
        """)

    def _toggle_bypass(self):
        """Toggle bypass state."""
        self.bypassed = not self.bypassed
        self._update_bypass_style()
        self._send_osc(OSC_PATHS['fb_bypass'], 1 if self.bypassed else 0)

    def _update_bypass_style(self):
        """Update bypass button appearance."""
        if self.bypassed:
            self.bypass_btn.setText("BYP")
            self.bypass_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['warning']};
                    color: {COLORS['warning_text']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 2px;
                }}
            """)
        else:
            self.bypass_btn.setText("ON")
            self.bypass_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['enabled']};
                    color: {COLORS['enabled_text']};
                    border: 1px solid {COLORS['border_active']};
                    border-radius: 2px;
                }}
            """)

    def _cycle_f1_mode(self):
        """Cycle F1 filter mode."""
        self.f1_mode = (self.f1_mode + 1) % len(self.MODES)
        self.f1_mode_btn.setText(self.MODES[self.f1_mode])
        self._send_osc(OSC_PATHS['fb_mode1'], self.f1_mode)

    def _cycle_f2_mode(self):
        """Cycle F2 filter mode."""
        self.f2_mode = (self.f2_mode + 1) % len(self.MODES)
        self.f2_mode_btn.setText(self.MODES[self.f2_mode])
        self._send_osc(OSC_PATHS['fb_mode2'], self.f2_mode)

    def _toggle_routing(self):
        """Toggle serial/parallel routing."""
        self.routing = 1 - self.routing
        self.routing_btn.setText(self.ROUTINGS[self.routing])
        self._send_osc(OSC_PATHS['fb_routing'], self.routing)

    def _on_f1_changed(self, value):
        self._send_osc(OSC_PATHS['fb_freq1'], value / 200.0)

    def _on_r1_changed(self, value):
        self._send_osc(OSC_PATHS['fb_reso1'], value / 200.0)

    def _on_f2_changed(self, value):
        self._send_osc(OSC_PATHS['fb_freq2'], value / 200.0)

    def _on_r2_changed(self, value):
        self._send_osc(OSC_PATHS['fb_reso2'], value / 200.0)

    def set_osc_bridge(self, osc_bridge):
        """Set OSC bridge."""
        self.osc_bridge = osc_bridge

    def _send_osc(self, path, value):
        """Send OSC message if connected."""
        if self.osc_bridge and self.osc_bridge.client:
            self.osc_bridge.client.send_message(path, [value])

    def sync_state(self):
        """Sync all state to SC."""
        self._send_osc(OSC_PATHS['fb_bypass'], 1 if self.bypassed else 0)
        self._send_osc(OSC_PATHS['fb_mode1'], self.f1_mode)
        self._send_osc(OSC_PATHS['fb_mode2'], self.f2_mode)
        self._send_osc(OSC_PATHS['fb_routing'], self.routing)
        self._send_osc(OSC_PATHS['fb_freq1'], self.f1_knob.value() / 200.0)
        self._send_osc(OSC_PATHS['fb_reso1'], self.r1_knob.value() / 200.0)
        self._send_osc(OSC_PATHS['fb_freq2'], self.f2_knob.value() / 200.0)
        self._send_osc(OSC_PATHS['fb_reso2'], self.r2_knob.value() / 200.0)

    def get_state(self) -> dict:
        """Get state for preset."""
        return {
            'bypass': self.bypassed,
            'f1_mode': self.f1_mode,
            'f2_mode': self.f2_mode,
            'routing': self.routing,
            'f1': self.f1_knob.value(),
            'r1': self.r1_knob.value(),
            'f2': self.f2_knob.value(),
            'r2': self.r2_knob.value(),
        }

    def set_state(self, state: dict):
        """Restore state from preset."""
        if 'bypass' in state and state['bypass'] != self.bypassed:
            self._toggle_bypass()
        if 'f1_mode' in state:
            self.f1_mode = state['f1_mode']
            self.f1_mode_btn.setText(self.MODES[self.f1_mode])
            self._send_osc(OSC_PATHS['fb_mode1'], self.f1_mode)
        if 'f2_mode' in state:
            self.f2_mode = state['f2_mode']
            self.f2_mode_btn.setText(self.MODES[self.f2_mode])
            self._send_osc(OSC_PATHS['fb_mode2'], self.f2_mode)
        if 'routing' in state:
            self.routing = state['routing']
            self.routing_btn.setText(self.ROUTINGS[self.routing])
            self._send_osc(OSC_PATHS['fb_routing'], self.routing)
        if 'f1' in state:
            self.f1_knob.setValue(state['f1'])
        if 'r1' in state:
            self.r1_knob.setValue(state['r1'])
        if 'f2' in state:
            self.f2_knob.setValue(state['f2'])
        if 'r2' in state:
            self.r2_knob.setValue(state['r2'])


# =============================================================================
# MASTER CHAIN (combines all)
# =============================================================================

class MasterChain(QWidget):
    """
    Unified master chain: Heat → Filter → EQ → Comp → Limiter → Output

    Signal flow:
    masterBus → Heat (insert) → Filter (insert) → EQ → Comp → Limiter → Output
    """

    # Forward signals from MasterSection
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
        self.osc_bridge = None
        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        """Build master chain UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(6)

        # Heat insert
        self.heat = HeatInsert()
        layout.addWidget(self.heat)

        # Filter insert
        self.filter = FilterInsert()
        layout.addWidget(self.filter)

        # MasterSection (EQ + Comp + Limiter + Output)
        self.master_section = MasterSection()
        layout.addWidget(self.master_section, stretch=1)

    def _connect_signals(self):
        """Forward all signals from MasterSection."""
        self.master_section.master_volume_changed.connect(self.master_volume_changed.emit)
        self.master_section.meter_mode_changed.connect(self.meter_mode_changed.emit)
        self.master_section.limiter_ceiling_changed.connect(self.limiter_ceiling_changed.emit)
        self.master_section.limiter_bypass_changed.connect(self.limiter_bypass_changed.emit)
        self.master_section.eq_lo_changed.connect(self.eq_lo_changed.emit)
        self.master_section.eq_mid_changed.connect(self.eq_mid_changed.emit)
        self.master_section.eq_hi_changed.connect(self.eq_hi_changed.emit)
        self.master_section.eq_lo_kill_changed.connect(self.eq_lo_kill_changed.emit)
        self.master_section.eq_mid_kill_changed.connect(self.eq_mid_kill_changed.emit)
        self.master_section.eq_hi_kill_changed.connect(self.eq_hi_kill_changed.emit)
        self.master_section.eq_locut_changed.connect(self.eq_locut_changed.emit)
        self.master_section.eq_bypass_changed.connect(self.eq_bypass_changed.emit)
        self.master_section.comp_threshold_changed.connect(self.comp_threshold_changed.emit)
        self.master_section.comp_ratio_changed.connect(self.comp_ratio_changed.emit)
        self.master_section.comp_attack_changed.connect(self.comp_attack_changed.emit)
        self.master_section.comp_release_changed.connect(self.comp_release_changed.emit)
        self.master_section.comp_makeup_changed.connect(self.comp_makeup_changed.emit)
        self.master_section.comp_sc_hpf_changed.connect(self.comp_sc_hpf_changed.emit)
        self.master_section.comp_bypass_changed.connect(self.comp_bypass_changed.emit)

    def set_osc_bridge(self, osc_bridge):
        """Set OSC bridge for all components."""
        self.osc_bridge = osc_bridge
        self.heat.set_osc_bridge(osc_bridge)
        self.filter.set_osc_bridge(osc_bridge)
        self.master_section.set_osc_bridge(osc_bridge)

    def sync_state(self):
        """Sync all state to SC on reconnect."""
        self.heat.sync_state()
        self.filter.sync_state()

    def set_levels(self, left, right, peak_left=None, peak_right=None):
        """Forward to MasterSection."""
        self.master_section.set_levels(left, right, peak_left, peak_right)

    def set_comp_gr(self, gr_db):
        """Forward to MasterSection."""
        self.master_section.set_comp_gr(gr_db)

    def get_volume(self):
        """Forward to MasterSection."""
        return self.master_section.get_volume()

    def set_volume(self, value):
        """Forward to MasterSection."""
        self.master_section.set_volume(value)

    def get_state(self) -> dict:
        """Get complete master chain state for preset."""
        state = self.master_section.get_state()
        state['heat'] = self.heat.get_state()
        state['filter'] = self.filter.get_state()
        return state

    def set_state(self, state: dict):
        """Apply complete master chain state from preset."""
        # Heat
        if 'heat' in state:
            self.heat.set_state(state['heat'])
        # Filter
        if 'filter' in state:
            self.filter.set_state(state['filter'])
        # MasterSection (pass full state, it ignores unknown keys)
        self.master_section.set_state(state)
