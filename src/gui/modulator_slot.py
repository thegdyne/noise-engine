"""
Modulator Slot v2 - Flat absolute positioning with per-type layouts
Each modulator type (LFO, Sloth, ARSEq+, SauceOfGrav) has its own layout dict
"""
from PyQt5.QtWidgets import QWidget, QLabel, QFrame, QSizePolicy, QToolTip
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QCursor

from .widgets import DragSlider, CycleButton
from .theme import COLORS, button_style, MONO_FONT, FONT_FAMILY, FONT_SIZES
from .mod_scope import ModScope
from src.config import (
    MOD_GENERATOR_CYCLE,
    MOD_LFO_WAVEFORMS,
    MOD_LFO_PHASES,
    MOD_LFO_MODES,
    MOD_POLARITY,
    MOD_CLOCK_RATES,
    MOD_LFO_FREQ_MIN,
    MOD_LFO_FREQ_MAX,
    MOD_OUTPUTS_PER_SLOT,
    get_mod_generator_custom_params,
    get_mod_generator_output_config,
    get_mod_output_labels,
    map_value,
)

# =============================================================================
# PER-TYPE LAYOUTS
# =============================================================================

LFO_LAYOUT = {
    'slot_width': 156,
    'slot_height': 280,

    # Header
    'mod_label_x': 5, 'mod_label_y': 5,
    'mod_label_w': 50, 'mod_label_h': 18,
    'selector_x': 58, 'selector_y': 3,
    'selector_w': 92, 'selector_h': 20,
    'sep_y': 24,

    # Scope
    'scope_x': 4, 'scope_y': 210,
    'scope_w': 148, 'scope_h': 60,

    # Params
    'params_y': 28,
    'label_h': 10,
    'mode_x': 6, 'mode_w': 28, 'mode_h': 22,
    'rate_x': 38, 'rate_w': 18, 'rate_h': 50,
    'rotate_x': 60, 'rotate_w': 28,

    # Clock rate selector
    'clk_rate_x': 92, 'clk_rate_y': 28,
    'clk_rate_w': 56, 'clk_rate_h': 20,

    # Outputs
    'outputs_y': 98,
    'output_row_h': 24,
    'out_label_w': 14,
    'wave_x': 22, 'wave_w': 40,
    'phase_x': 64, 'phase_w': 38,
    'pol_x': 104, 'pol_w': 28,
}

SLOTH_LAYOUT = {
    'slot_width': 156,
    'slot_height': 280,

    # Header
    'mod_label_x': 5, 'mod_label_y': 5,
    'mod_label_w': 50, 'mod_label_h': 18,
    'selector_x': 58, 'selector_y': 3,
    'selector_w': 92, 'selector_h': 20,
    'sep_y': 24,

    # Scope
    'scope_x': 4, 'scope_y': 210,
    'scope_w': 148, 'scope_h': 60,

    # Params
    'params_y': 30,
    'label_h': 10,
    'mode_x': 22, 'mode_w': 28, 'mode_h': 22,

    # Outputs
    'outputs_y': 98,
    'output_row_h': 24,
    'out_label_w': 14,
    'pol_x': 22, 'pol_w': 28,
}

ARSEQ_LAYOUT = {
    'slot_width': 156,
    'slot_height': 280,

    # Header
    'mod_label_x': 4, 'mod_label_y': 4,
    'mod_label_w': 50, 'mod_label_h': 18,
    'selector_x': 58, 'selector_y': 3,
    'selector_w': 92, 'selector_h': 20,
    'sep_y': 24,

    # Scope
    'scope_x': 4, 'scope_y': 210,
    'scope_w': 148, 'scope_h': 60,

    # Params
    'params_y': 30,
    'label_h': 10,
    'mode_x': 6, 'mode_w': 28, 'mode_h': 22,
    'clk_x': 38, 'clk_w': 28,
    'rate_x': 70, 'rate_w': 18, 'rate_h': 60,

    # Clock rate selector
    'clk_rate_x': 92, 'clk_rate_y': 30,
    'clk_rate_w': 56, 'clk_rate_h': 20,

    # Outputs
    'outputs_y': 106,
    'output_row_h': 24,
    'out_label_w': 12,
    'atk_x': 16, 'atk_w': 45,
    'rel_x': 66, 'rel_w': 45,
    'sync_x': 112, 'sync_w': 24,
    'pol_x': 138, 'pol_w': 16,
}

SAUCE_LAYOUT = {
    'slot_width': 156,
    'slot_height': 280,

    # Header
    'mod_label_x': 4, 'mod_label_y': 4,
    'mod_label_w': 50, 'mod_label_h': 18,
    'selector_x': 58, 'selector_y': 3,
    'selector_w': 92, 'selector_h': 20,
    'sep_y': 24,

    # Scope
    'scope_x': 4, 'scope_y': 210,
    'scope_w': 148, 'scope_h': 60,

    # Params
    'params_y': 30,
    'label_h': 10,
    'clk_x': 4, 'clk_w': 28, 'clk_h': 22,
    'rate_x': 34, 'rate_w': 18,
    'depth_x': 54, 'depth_w': 18,
    'grav_x': 74, 'grav_w': 18,
    'reso_x': 94, 'reso_w': 18,
    'excur_x': 114, 'excur_w': 18,
    'calm_x': 134, 'calm_w': 18,
    'slider_h': 60,

    # Outputs
    'outputs_y': 108,
    'output_row_h': 24,
    'out_label_w': 12,
    'tens_x': 14, 'tens_w': 55,
    'mass_x': 70, 'mass_w': 55,
    'pol_x': 130, 'pol_w': 20,
}

# Empty uses LFO layout as base
EMPTY_LAYOUT = LFO_LAYOUT

def get_layout(gen_name):
    """Get layout dict for generator type."""
    return {
        'LFO': LFO_LAYOUT,
        'Sloth': SLOTH_LAYOUT,
        'ARSEq+': ARSEQ_LAYOUT,
        'SauceOfGrav': SAUCE_LAYOUT,
        'Empty': EMPTY_LAYOUT,
    }.get(gen_name, LFO_LAYOUT)

# Mode labels
MOD_SLOTH_MODES = ["TOR", "APA", "INE"]
ARSEQ_SYNC_MODES = ["SYN", "LOP"]
LFO_ROTATE_PHASES = ["0", "45", "90", "135", "180", "225", "270", "315"]


class ModulatorSlot(QWidget):
    """A single modulator slot with 4 outputs - flat absolute positioning."""

    # Signals
    generator_changed = pyqtSignal(int, str)
    parameter_changed = pyqtSignal(int, str, float)
    output_wave_changed = pyqtSignal(int, int, int)
    output_phase_changed = pyqtSignal(int, int, int)
    output_polarity_changed = pyqtSignal(int, int, int)
    clock_rate_changed = pyqtSignal(int, str)  # slot_id, rate_label

    # ARSEq+ envelope signals
    env_attack_changed = pyqtSignal(int, int, float)
    env_release_changed = pyqtSignal(int, int, float)
    env_curve_changed = pyqtSignal(int, int, float)
    env_sync_mode_changed = pyqtSignal(int, int, int)
    env_loop_rate_changed = pyqtSignal(int, int, int)

    # SauceOfGrav output signals
    tension_changed = pyqtSignal(int, int, float)
    mass_changed = pyqtSignal(int, int, float)

    def __init__(self, slot_id, default_generator="Empty", parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.slot_id = slot_id
        self.setObjectName(f"mod{slot_id}_slot")
        self.default_generator = default_generator
        self.generator_name = "Empty"
        self.output_config = "fixed"

        # Use default layout for sizing
        L = get_layout(default_generator)
        self.setFixedWidth(L['slot_width'])
        self.setMinimumHeight(L['slot_height'])
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.MinimumExpanding)

        # Storage for dynamic widgets
        self.param_widgets = []
        self.param_sliders = {}
        self.output_widgets = []
        self.output_rows = []

        self._build_static_ui()
        self.update_for_generator(default_generator)

    # =========================================================================
    # UI Building - Static elements
    # =========================================================================

    def _build_static_ui(self):
        """Build static widgets (header, separator, scope)."""
        L = get_layout(self.default_generator)

        # Header
        self.id_label = QLabel(f"MOD {self.slot_id}", self)
        self.id_label.setFont(QFont(FONT_FAMILY, FONT_SIZES['small'], QFont.Bold))
        self.id_label.setStyleSheet(f"color: {COLORS['text_bright']};")
        self.id_label.setGeometry(L['mod_label_x'], L['mod_label_y'],
                                  L['mod_label_w'], L['mod_label_h'])

        initial_idx = MOD_GENERATOR_CYCLE.index(self.default_generator) if self.default_generator in MOD_GENERATOR_CYCLE else 0
        self.gen_button = CycleButton(MOD_GENERATOR_CYCLE, initial_index=initial_idx, parent=self)
        self.gen_button.setGeometry(L['selector_x'], L['selector_y'],
                                    L['selector_w'], L['selector_h'])
        self.gen_button.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        self.gen_button.setStyleSheet(button_style('submenu'))
        self.gen_button.text_alignment = Qt.AlignVCenter | Qt.AlignLeft
        self.gen_button.text_padding_lr = 4
        self.gen_button.value_changed.connect(self._on_generator_changed)

        # Separator
        self.separator = QFrame(self)
        self.separator.setGeometry(4, L['sep_y'], L['slot_width'] - 8, 1)
        self.separator.setStyleSheet(f"background-color: {COLORS['text_bright']};")

        # Scope
        self.scope = ModScope(history_length=100, parent=self)
        self.scope.setGeometry(L['scope_x'], L['scope_y'], L['scope_w'], L['scope_h'])
        self.scope.setStyleSheet(f"border: 1px solid {COLORS['border']}; border-radius: 3px;")

        self._update_empty_style()

    # =========================================================================
    # UI Building - Dynamic elements (per-type)
    # =========================================================================

    def _clear_dynamic_widgets(self):
        """Remove all dynamic param and output widgets."""
        for w in self.param_widgets:
            w.deleteLater()
        self.param_widgets = []
        self.param_sliders = {}

        for w in self.output_widgets:
            w.deleteLater()
        self.output_widgets = []
        self.output_rows = []
        self._curve_sliders = []
        self._loop_rate_btns = []

    def _build_lfo_ui(self):
        """Build LFO-specific UI."""
        L = LFO_LAYOUT
        y = L['params_y']

        # MODE (CLK/FREE)
        lbl = QLabel("CLK", self)
        lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(f"color: {COLORS['text']};")
        lbl.setGeometry(L['mode_x'], y, L['mode_w'], L['label_h'])
        self.param_widgets.append(lbl)

        mode_btn = CycleButton(MOD_LFO_MODES, initial_index=0, parent=self)
        mode_btn.setGeometry(L['mode_x'], y + L['label_h'] + 2, L['mode_w'], L['mode_h'])
        mode_btn.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        mode_btn.setStyleSheet(button_style('submenu'))
        mode_btn.setToolTip("CLK: sync to clock\nFREE: manual frequency")
        mode_btn.index_changed.connect(lambda idx: self._on_mode_changed('mode', idx))
        self.param_widgets.append(mode_btn)
        self.param_sliders['mode'] = mode_btn

        # RATE slider
        lbl = QLabel("RATE", self)
        lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(f"color: {COLORS['text']};")
        lbl.setGeometry(L['rate_x'], y, L['rate_w'], L['label_h'])
        self.param_widgets.append(lbl)

        rate_slider = DragSlider(parent=self)
        rate_slider.setRange(0, 1000)
        rate_slider.setValue(182)  # /16 clock division
        rate_slider.setGeometry(L['rate_x'], y + L['label_h'], L['rate_w'], L['rate_h'])
        rate_slider.valueChanged.connect(lambda v: self._on_rate_changed(v))
        rate_slider.valueChanged.connect(lambda v: self._update_lfo_rate_tooltip(v))
        self.param_widgets.append(rate_slider)
        self.param_sliders['rate'] = rate_slider
        self._update_lfo_rate_tooltip(182)  # Sets initial tooltip

        # ROTATE button
        lbl = QLabel("ROT", self)
        lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(f"color: {COLORS['text']};")
        lbl.setGeometry(L['rotate_x'], y, L['rotate_w'], L['label_h'])
        self.param_widgets.append(lbl)

        rot_btn = CycleButton(LFO_ROTATE_PHASES, initial_index=0, parent=self)
        rot_btn.setGeometry(L['rotate_x'], y + L['label_h'] + 2, L['rotate_w'], L['mode_h'])
        rot_btn.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        rot_btn.setStyleSheet(button_style('submenu'))
        rot_btn.setToolTip("Global phase rotation\nShifts all outputs together")
        rot_btn.index_changed.connect(lambda idx: self._on_mode_changed('rotate', idx))
        self.param_widgets.append(rot_btn)
        self.param_sliders['rotate'] = rot_btn

        # CLOCK RATE selector (for CLK mode)
        lbl = QLabel("CLK", self)
        lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(f"color: {COLORS['text']};")
        lbl.setGeometry(L['clk_rate_x'], L['clk_rate_y'], L['clk_rate_w'], L['label_h'])
        self.param_widgets.append(lbl)

        self.clock_rate_btn = CycleButton(MOD_CLOCK_RATES, initial_index=6, parent=self)  # Default CLK
        self.clock_rate_btn.setGeometry(L['clk_rate_x'], L['clk_rate_y'] + L['label_h'] + 2, L['clk_rate_w'], L['mode_h'])
        self.clock_rate_btn.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        self.clock_rate_btn.setStyleSheet(button_style('submenu'))
        self.clock_rate_btn.setToolTip("Clock rate\nUse in CLK mode for tempo-synced modulation")
        self.clock_rate_btn.index_changed.connect(lambda idx: self._on_clock_rate_changed(idx))
        self.param_widgets.append(self.clock_rate_btn)

        # Show all param widgets
        for w in self.param_widgets:
            w.show()

        # Output rows
        output_labels = get_mod_output_labels('LFO')
        for i in range(MOD_OUTPUTS_PER_SLOT):
            row_y = L['outputs_y'] + i * L['output_row_h']
            row_widgets = self._build_lfo_output_row(i, row_y, output_labels[i], L)
            self.output_rows.append(row_widgets)

    def _build_lfo_output_row(self, idx, y, label, L):
        """Build single LFO output row."""
        row_widgets = {}

        # Label
        lbl = QLabel(label, self)
        lbl.setFont(QFont(MONO_FONT, FONT_SIZES['small'], QFont.Bold))
        lbl.setStyleSheet(f"color: {COLORS['text_bright']};")
        lbl.setGeometry(L['mod_label_x'], y, L['out_label_w'], L['output_row_h'])
        self.output_widgets.append(lbl)
        row_widgets['label'] = lbl

        # Wave
        wave_btn = CycleButton(MOD_LFO_WAVEFORMS, initial_index=0, parent=self)
        wave_btn.setGeometry(L['wave_x'], y, L['wave_w'], 22)
        wave_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        wave_btn.setStyleSheet(button_style('submenu'))
        wave_btn.setToolTip("Waveform shape\nTri, Sin, Saw, Sqr, S&H, Noise")
        wave_btn.value_changed.connect(lambda w, i=idx: self._on_wave_changed(i, MOD_LFO_WAVEFORMS.index(w)))
        self.output_widgets.append(wave_btn)
        row_widgets['wave'] = wave_btn

        # Phase
        default_phases = [0, 3, 5, 6]
        phase_labels = [f"{p}" for p in MOD_LFO_PHASES]
        phase_btn = CycleButton(phase_labels, initial_index=default_phases[idx] if idx < 4 else 0, parent=self)
        phase_btn.setGeometry(L['phase_x'], y, L['phase_w'], 22)
        phase_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        phase_btn.setStyleSheet(button_style('submenu'))
        phase_btn.setToolTip("Phase offset\n0 to 315 in 45 steps")
        phase_btn.value_changed.connect(lambda p, i=idx, pl=phase_labels: self._on_phase_changed(i, pl.index(p)))
        self.output_widgets.append(phase_btn)
        row_widgets['phase'] = phase_btn

        # Polarity
        pol_btn = CycleButton(MOD_POLARITY, initial_index=0, parent=self)
        pol_btn.setGeometry(L['pol_x'], y, L['pol_w'], 22)
        pol_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        pol_btn.setStyleSheet(button_style('submenu'))
        pol_btn.setToolTip("NORM: 0 to +1\nINV: 0 to -1")
        pol_btn.value_changed.connect(lambda p, i=idx: self._on_polarity_changed(i, MOD_POLARITY.index(p)))
        self.output_widgets.append(pol_btn)
        row_widgets['polarity'] = pol_btn

        for w in row_widgets.values():
            w.show()

        return row_widgets

    def _build_sloth_ui(self):
        """Build Sloth-specific UI."""
        L = SLOTH_LAYOUT
        y = L['params_y']

        # MODE (TOR/APA/INE)
        lbl = QLabel("MODE", self)
        lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(f"color: {COLORS['text']};")
        lbl.setGeometry(L['mode_x'], y, L['mode_w'], L['label_h'])
        self.param_widgets.append(lbl)

        mode_btn = CycleButton(MOD_SLOTH_MODES, initial_index=1, parent=self)
        mode_btn.setGeometry(L['mode_x'], y + L['label_h'] + 2, L['mode_w'], L['mode_h'])
        mode_btn.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        mode_btn.setStyleSheet(button_style('submenu'))
        mode_btn.setToolTip("Torpor: 15-30s\nApathy: 60-90s\nInertia: 30-40min")
        mode_btn.index_changed.connect(lambda idx: self._on_mode_changed('mode', idx))
        self.param_widgets.append(mode_btn)
        self.param_sliders['mode'] = mode_btn

        for w in self.param_widgets:
            w.show()

        # Output rows
        output_labels = get_mod_output_labels('Sloth')
        for i in range(MOD_OUTPUTS_PER_SLOT):
            row_y = L['outputs_y'] + i * L['output_row_h']
            row_widgets = self._build_sloth_output_row(i, row_y, output_labels[i], L)
            self.output_rows.append(row_widgets)

    def _build_sloth_output_row(self, idx, y, label, L):
        """Build single Sloth output row."""
        row_widgets = {}

        # Label
        lbl = QLabel(label, self)
        lbl.setFont(QFont(MONO_FONT, FONT_SIZES['small'], QFont.Bold))
        lbl.setStyleSheet(f"color: {COLORS['text_bright']};")
        lbl.setGeometry(L['mod_label_x'], y, L['out_label_w'], L['output_row_h'])
        self.output_widgets.append(lbl)
        row_widgets['label'] = lbl

        # Polarity only
        pol_btn = CycleButton(MOD_POLARITY, initial_index=0, parent=self)
        pol_btn.setGeometry(L['pol_x'], y, L['pol_w'], 22)
        pol_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        pol_btn.setStyleSheet(button_style('submenu'))
        pol_btn.setToolTip("NORM: 0 to +1\nINV: 0 to -1")
        pol_btn.value_changed.connect(lambda p, i=idx: self._on_polarity_changed(i, MOD_POLARITY.index(p)))
        self.output_widgets.append(pol_btn)
        row_widgets['polarity'] = pol_btn

        for w in row_widgets.values():
            w.show()

        return row_widgets

    def _build_arseq_ui(self):
        """Build ARSEq+-specific UI."""
        L = ARSEQ_LAYOUT
        y = L['params_y']

        # MODE (SEQ/PAR) - get tooltip from config
        arseq_params = {p['key']: p for p in get_mod_generator_custom_params('ARSEq+')}
        
        lbl = QLabel("MODE", self)
        lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(f"color: {COLORS['text']};")
        lbl.setGeometry(L['mode_x'], y, L['mode_w'], L['label_h'])
        self.param_widgets.append(lbl)

        mode_btn = CycleButton(["SEQ", "PAR"], initial_index=0, parent=self)
        mode_btn.setGeometry(L['mode_x'], y + L['label_h'] + 2, L['mode_w'], L['mode_h'])
        mode_btn.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        mode_btn.setStyleSheet(button_style('submenu'))
        mode_btn.setToolTip(arseq_params.get('mode', {}).get('tooltip', "SEQ: sequence\nPAR: parallel"))
        mode_btn.index_changed.connect(lambda idx: self._on_mode_changed('mode', idx))
        self.param_widgets.append(mode_btn)
        self.param_sliders['mode'] = mode_btn

        # CLK (CLK/FREE)
        lbl = QLabel("CLK", self)
        lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(f"color: {COLORS['text']};")
        lbl.setGeometry(L['clk_x'], y, L['clk_w'], L['label_h'])
        self.param_widgets.append(lbl)

        clk_btn = CycleButton(MOD_LFO_MODES, initial_index=0, parent=self)
        clk_btn.setGeometry(L['clk_x'], y + L['label_h'] + 2, L['clk_w'], L['mode_h'])
        clk_btn.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        clk_btn.setStyleSheet(button_style('submenu'))
        clk_btn.setToolTip(arseq_params.get('clock_mode', {}).get('tooltip', "CLK: sync\nFREE: manual"))
        clk_btn.index_changed.connect(lambda idx: self._on_mode_changed('clock_mode', idx))
        self.param_widgets.append(clk_btn)
        self.param_sliders['clock_mode'] = clk_btn

        # RATE slider
        lbl = QLabel("RATE", self)
        lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(f"color: {COLORS['text']};")
        lbl.setGeometry(L['rate_x'], y, L['rate_w'], L['label_h'])
        self.param_widgets.append(lbl)

        rate_slider = DragSlider(parent=self)
        rate_slider.setRange(0, 1000)
        rate_slider.setValue(364)  # /4 clock division
        rate_slider.setGeometry(L['rate_x'], y + L['label_h'], L['rate_w'], L['rate_h'])
        rate_slider.valueChanged.connect(lambda v: self._on_rate_changed(v))
        rate_slider.valueChanged.connect(lambda v: self._update_arseq_rate_tooltip(v))
        self.param_widgets.append(rate_slider)
        self.param_sliders['rate'] = rate_slider
        self._update_arseq_rate_tooltip(364)

        # CLOCK RATE selector (for CLK mode)
        lbl = QLabel("CLK", self)
        lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(f"color: {COLORS['text']};")
        lbl.setGeometry(L['clk_rate_x'], L['clk_rate_y'], L['clk_rate_w'], L['label_h'])
        self.param_widgets.append(lbl)

        self.clock_rate_btn = CycleButton(MOD_CLOCK_RATES, initial_index=6, parent=self)  # Default CLK
        self.clock_rate_btn.setGeometry(L['clk_rate_x'], L['clk_rate_y'] + L['label_h'] + 2, L['clk_rate_w'], L['mode_h'])
        self.clock_rate_btn.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        self.clock_rate_btn.setStyleSheet(button_style('submenu'))
        self.clock_rate_btn.setToolTip("Clock rate\nUse in CLK mode for tempo-synced envelopes")
        self.clock_rate_btn.index_changed.connect(lambda idx: self._on_clock_rate_changed(idx))
        self.param_widgets.append(self.clock_rate_btn)

        for w in self.param_widgets:
            w.show()

        # Output rows
        output_labels = get_mod_output_labels('ARSEq+')
        for i in range(MOD_OUTPUTS_PER_SLOT):
            row_y = L['outputs_y'] + i * L['output_row_h']
            row_widgets = self._build_arseq_output_row(i, row_y, output_labels[i], L)
            self.output_rows.append(row_widgets)

    def _build_arseq_output_row(self, idx, y, label, L):
        """Build single ARSEq+ output row."""
        row_widgets = {}

        # Label
        lbl = QLabel(label, self)
        lbl.setFont(QFont(MONO_FONT, FONT_SIZES['small'], QFont.Bold))
        lbl.setStyleSheet(f"color: {COLORS['text_bright']};")
        lbl.setGeometry(L['mod_label_x'], y, L['out_label_w'], L['output_row_h'])
        self.output_widgets.append(lbl)
        row_widgets['label'] = lbl

        # ATK slider
        atk = DragSlider(parent=self)
        atk.setRange(0, 1000)
        atk.setOrientation(Qt.Horizontal)
        atk.setGeometry(L['atk_x'], y + 2, L['atk_w'], 20)
        atk.setValue(0)
        atk.setToolTip("Attack: 0%")
        atk.valueChanged.connect(lambda v, s=atk: self._show_slider_tooltip(s, f"Attack: {v / 10:.0f}%"))
        atk.valueChanged.connect(lambda v, i=idx: self._on_env_attack_changed(i, v))
        self.output_widgets.append(atk)
        row_widgets['atk'] = atk

        # REL slider
        rel = DragSlider(parent=self)
        rel.setRange(0, 1000)
        rel.setOrientation(Qt.Horizontal)
        rel.setGeometry(L['rel_x'], y + 2, L['rel_w'], 20)
        rel.setValue(500)
        rel.setToolTip("Release: 50%")
        rel.valueChanged.connect(lambda v, s=rel: self._show_slider_tooltip(s, f"Release: {v / 10:.0f}%"))
        rel.valueChanged.connect(lambda v, i=idx: self._on_env_release_changed(i, v))
        self.output_widgets.append(rel)
        row_widgets['rel'] = rel

        # Hidden curve (not added to row_widgets to avoid show() call)
        crv = DragSlider(parent=self)
        crv.setRange(0, 1000)
        crv.setValue(500)
        crv.setGeometry(0, 0, 0, 0)  # Zero size
        crv.setVisible(False)
        crv.valueChanged.connect(lambda v, i=idx: self._on_env_curve_changed(i, v))
        self.output_widgets.append(crv)
        # Store reference but don't add to row_widgets (would get .show() called)
        self._curve_sliders = getattr(self, '_curve_sliders', [])
        self._curve_sliders.append(crv)

        # Sync mode
        sync_btn = CycleButton(ARSEQ_SYNC_MODES, initial_index=0, parent=self)
        sync_btn.setGeometry(L['sync_x'], y, L['sync_w'], 22)
        sync_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        sync_btn.setStyleSheet(button_style('submenu'))
        sync_btn.setToolTip("SYN: sync to master clock\nLOP: independent loop\nShift+click in LOP mode for rate")
        sync_btn.index_changed.connect(lambda m, i=idx: self._on_env_sync_mode_changed(i, m))
        self.output_widgets.append(sync_btn)
        row_widgets['sync_mode'] = sync_btn

        # Loop rate (hidden - not in row_widgets to avoid show() call)
        loop_btn = CycleButton(MOD_CLOCK_RATES, initial_index=6, parent=self)
        loop_btn.setGeometry(L['sync_x'], y, L['sync_w'], 22)
        loop_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        loop_btn.setStyleSheet(button_style('submenu'))
        loop_btn.setVisible(False)
        loop_btn.index_changed.connect(lambda r, i=idx: self._on_env_loop_rate_changed(i, r))
        self.output_widgets.append(loop_btn)
        # Store reference separately
        self._loop_rate_btns = getattr(self, '_loop_rate_btns', [])
        self._loop_rate_btns.append(loop_btn)

        # Toggle rate visibility on shift+click
        def toggle_rate(s=sync_btn, r=loop_btn):
            if s.index == 1:  # Only works in LOP mode
                r.setVisible(not r.isVisible())
                s.setVisible(not r.isVisible())
        sync_btn.shift_click_callback = toggle_rate
        loop_btn.shift_click_callback = toggle_rate

        # Polarity
        pol_btn = CycleButton(MOD_POLARITY, initial_index=0, parent=self)
        pol_btn.setGeometry(L['pol_x'], y, L['pol_w'], 22)
        pol_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        pol_btn.setStyleSheet(button_style('submenu'))
        pol_btn.setToolTip("NORM: 0 to +1\nINV: 0 to -1")
        pol_btn.value_changed.connect(lambda p, i=idx: self._on_polarity_changed(i, MOD_POLARITY.index(p)))
        self.output_widgets.append(pol_btn)
        row_widgets['polarity'] = pol_btn

        for w in row_widgets.values():
            w.show()

        return row_widgets

    def _build_sauce_ui(self):
        """Build SauceOfGrav-specific UI."""
        L = SAUCE_LAYOUT
        y = L['params_y']

        # Get tooltips from config
        sauce_params = {p['key']: p for p in get_mod_generator_custom_params('SauceOfGrav')}

        # CLK
        lbl = QLabel("CLK", self)
        lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(f"color: {COLORS['text']};")
        lbl.setGeometry(L['clk_x'], y, L['clk_w'], L['label_h'])
        self.param_widgets.append(lbl)

        clk_btn = CycleButton(MOD_LFO_MODES, initial_index=0, parent=self)
        clk_btn.setGeometry(L['clk_x'], y + L['label_h'] + 2, L['clk_w'], L['clk_h'])
        clk_btn.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        clk_btn.setStyleSheet(button_style('submenu'))
        clk_btn.setToolTip(sauce_params.get('clock_mode', {}).get('tooltip', "CLK: sync to transport\nFREE: free-running"))
        clk_btn.index_changed.connect(lambda idx: self._on_mode_changed('clock_mode', idx))
        self.param_widgets.append(clk_btn)
        self.param_sliders['clock_mode'] = clk_btn

        # Sliders: RATE, DEPTH, GRAV, RESO, EXCUR, CALM - use sauce_params from above
        slider_defs = [
            ('rate', 'RATE', L['rate_x'], L['rate_w']),
            ('depth', 'DPTH', L['depth_x'], L['depth_w']),
            ('gravity', 'GRAV', L['grav_x'], L['grav_w']),
            ('resonance', 'RESO', L['reso_x'], L['reso_w']),
            ('excursion', 'EXCR', L['excur_x'], L['excur_w']),
            ('calm', 'CALM', L['calm_x'], L['calm_w']),
        ]

        for key, label_text, x, w in slider_defs:
            lbl = QLabel(label_text, self)
            lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"color: {COLORS['text']};")
            lbl.setGeometry(x, y, w, L['label_h'])
            self.param_widgets.append(lbl)

            slider = DragSlider(parent=self)
            slider.setRange(0, 1000)
            slider.setValue(500)
            slider.setGeometry(x, y + L['label_h'], w, L['slider_h'])
            # Use config tooltip if available
            param_info = sauce_params.get(key, {})
            base_tooltip = param_info.get('tooltip', key.capitalize())
            slider.setToolTip(f"{base_tooltip}\nValue: 50%")
            slider.valueChanged.connect(lambda v, k=key: self._on_sauce_param_changed(k, v))
            slider.valueChanged.connect(lambda v, s=slider, t=base_tooltip: self._show_slider_tooltip(s, f"{t}\nValue: {v / 10:.0f}%"))
            self.param_widgets.append(slider)
            self.param_sliders[key] = slider

        for w in self.param_widgets:
            w.show()

        # Output rows
        output_labels = get_mod_output_labels('SauceOfGrav')
        for i in range(MOD_OUTPUTS_PER_SLOT):
            row_y = L['outputs_y'] + i * L['output_row_h']
            row_widgets = self._build_sauce_output_row(i, row_y, output_labels[i], L)
            self.output_rows.append(row_widgets)

    def _build_sauce_output_row(self, idx, y, label, L):
        """Build single SauceOfGrav output row."""
        row_widgets = {}

        # Label
        lbl = QLabel(label, self)
        lbl.setFont(QFont(MONO_FONT, FONT_SIZES['small'], QFont.Bold))
        lbl.setStyleSheet(f"color: {COLORS['text_bright']};")
        lbl.setGeometry(L['mod_label_x'], y, L['out_label_w'], L['output_row_h'])
        self.output_widgets.append(lbl)
        row_widgets['label'] = lbl

        # TENS slider
        tension_defaults = [300, 450, 550, 700]
        default_tens = tension_defaults[idx] if idx < 4 else 500
        tens = DragSlider(parent=self)
        tens.setRange(0, 1000)
        tens.setOrientation(Qt.Horizontal)
        tens.setGeometry(L['tens_x'], y + 2, L['tens_w'], 20)
        tens.setValue(default_tens)
        tens.setToolTip(f"Tension: {default_tens / 10:.0f}%")
        tens.valueChanged.connect(lambda v, s=tens: self._show_slider_tooltip(s, f"Tension: {v / 10:.0f}%"))
        tens.valueChanged.connect(lambda v, i=idx: self._on_tension_changed(i, v))
        self.output_widgets.append(tens)
        row_widgets['tension'] = tens

        # MASS slider
        mass_defaults = [650, 550, 450, 350]
        default_mass = mass_defaults[idx] if idx < 4 else 500
        mass = DragSlider(parent=self)
        mass.setRange(0, 1000)
        mass.setOrientation(Qt.Horizontal)
        mass.setGeometry(L['mass_x'], y + 2, L['mass_w'], 20)
        mass.setValue(default_mass)
        mass.setToolTip(f"Mass: {default_mass / 10:.0f}%")
        mass.valueChanged.connect(lambda v, s=mass: self._show_slider_tooltip(s, f"Mass: {v / 10:.0f}%"))
        mass.valueChanged.connect(lambda v, i=idx: self._on_mass_changed(i, v))
        self.output_widgets.append(mass)
        row_widgets['mass'] = mass

        # Polarity
        pol_btn = CycleButton(MOD_POLARITY, initial_index=0, parent=self)
        pol_btn.setGeometry(L['pol_x'], y, L['pol_w'], 22)
        pol_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        pol_btn.setStyleSheet(button_style('submenu'))
        pol_btn.setToolTip("NORM: 0 to +1\nINV: 0 to -1")
        pol_btn.value_changed.connect(lambda p, i=idx: self._on_polarity_changed(i, MOD_POLARITY.index(p)))
        self.output_widgets.append(pol_btn)
        row_widgets['polarity'] = pol_btn

        for w in row_widgets.values():
            w.show()

        return row_widgets

    # =========================================================================
    # Generator Change
    # =========================================================================

    def _on_generator_changed(self, gen_name):
        """Handle generator selection change."""
        self.update_for_generator(gen_name)
        self.generator_changed.emit(self.slot_id, gen_name)

    def update_for_generator(self, gen_name):
        """Rebuild UI for selected generator."""
        self.generator_name = gen_name
        self.output_config = get_mod_generator_output_config(gen_name)

        self._clear_dynamic_widgets()

        if gen_name == "Empty":
            self._setup_empty_state()
            return

        # Build type-specific UI
        if gen_name == "LFO":
            self._build_lfo_ui()
        elif gen_name == "Sloth":
            self._build_sloth_ui()
        elif gen_name == "ARSEq+":
            self._build_arseq_ui()
        elif gen_name == "SauceOfGrav":
            self._build_sauce_ui()

        # Set objectNames for boid glow visualization
        self._update_param_object_names()

        self._update_style_for_generator(gen_name)

    def _setup_empty_state(self):
        """Setup minimal UI for Empty generator."""
        self.scope.clear()
        self.scope.setEnabled(False)
        self._update_empty_style()

    def _update_empty_style(self):
        """Apply empty/inactive styling."""
        self.setStyleSheet(f"""
            ModulatorSlot {{
                border: 2px solid {COLORS['border']};
                border-radius: 6px;
                background-color: {COLORS['background']};
            }}
        """)

    def _update_style_for_generator(self, gen_name):
        """Apply styling based on generator type."""
        accent_key = {
            "LFO": "accent_mod_lfo",
            "Sloth": "accent_mod_sloth",
            "ARSEq+": "accent_mod_arseq_plus",
            "SauceOfGrav": "accent_mod_sauce_of_grav",
        }.get(gen_name, "accent_mod_lfo")
        accent = COLORS.get(accent_key, COLORS['accent_mod_lfo'])

        self.setStyleSheet(f"""
            ModulatorSlot {{
                border: 2px solid {accent};
                border-radius: 6px;
                background-color: {COLORS['background_light']};
            }}
        """)
        self.scope.setEnabled(True)
        self.scope.clear()

    # =========================================================================
    # Object Name Management (for boid glow)
    # =========================================================================

    def _update_param_object_names(self):
        """
        Set objectNames on param widgets to match unified bus target keys.

        The unified bus uses mod_{slot}_p{index} format. We map param keys
        to their index in the custom_params list.
        """
        custom_params = get_mod_generator_custom_params(self.generator_name)
        key_to_index = {p['key']: i for i, p in enumerate(custom_params)}

        for key, widget in self.param_sliders.items():
            if key in key_to_index:
                p_index = key_to_index[key]
                widget.setObjectName(f"mod_{self.slot_id}_p{p_index}")

    # =========================================================================
    # Event Handlers
    # =========================================================================

    def _on_mode_changed(self, key, index):
        """Handle mode button change."""
        self.parameter_changed.emit(self.slot_id, key, float(index))

    def _on_rate_changed(self, value):
        """Handle rate slider change."""
        normalized = value / 1000.0
        # Get param config for proper mapping
        for param in get_mod_generator_custom_params(self.generator_name):
            if param.get('key') == 'rate':
                real_value = map_value(normalized, param)
                self.parameter_changed.emit(self.slot_id, 'rate', real_value)
                break

    def _on_clock_rate_changed(self, index):
        """Handle clock rate selector change."""
        if hasattr(self, 'clock_rate_btn'):
            rate_label = self.clock_rate_btn.get_value()
            self.clock_rate_changed.emit(self.slot_id, rate_label)

    def _update_lfo_rate_tooltip(self, value):
        """Update LFO rate slider tooltip with current value."""
        if 'rate' not in self.param_sliders:
            return
        slider = self.param_sliders['rate']
        mode_btn = self.param_sliders.get('mode')

        # Check if CLK mode (index 0) or FREE mode (index 1)
        is_clk_mode = mode_btn.index == 0 if mode_btn else True

        if is_clk_mode:
            # Map to clock division
            idx = int((value / 1000.0) * (len(MOD_CLOCK_RATES) - 1))
            idx = max(0, min(idx, len(MOD_CLOCK_RATES) - 1))
            division = MOD_CLOCK_RATES[idx]
            tip = f"Rate: {division}"
        else:
            # Map to frequency
            normalized = value / 1000.0
            freq = MOD_LFO_FREQ_MIN * ((MOD_LFO_FREQ_MAX / MOD_LFO_FREQ_MIN) ** normalized)
            tip = f"Rate: {freq:.2f} Hz"
        
        slider.setToolTip(tip)
        QToolTip.showText(QCursor.pos(), tip, slider)

    def _update_arseq_rate_tooltip(self, value):
        """Update ARSEq+ rate slider tooltip with current value."""
        if 'rate' not in self.param_sliders:
            return
        slider = self.param_sliders['rate']
        clk_btn = self.param_sliders.get('clock_mode')

        # Check if CLK mode (index 0) or FREE mode (index 1)
        is_clk_mode = clk_btn.index == 0 if clk_btn else True

        if is_clk_mode:
            # Map to clock division
            idx = int((value / 1000.0) * (len(MOD_CLOCK_RATES) - 1))
            idx = max(0, min(idx, len(MOD_CLOCK_RATES) - 1))
            division = MOD_CLOCK_RATES[idx]
            tip = f"Rate: {division}"
        else:
            # Show percentage for free mode
            tip = f"Rate: {value / 10:.0f}%"
        
        slider.setToolTip(tip)
        QToolTip.showText(QCursor.pos(), tip, slider)

    def _show_slider_tooltip(self, slider, tip):
        """Set tooltip and show it immediately at cursor position."""
        slider.setToolTip(tip)
        QToolTip.showText(QCursor.pos(), tip, slider)

    def _on_sauce_param_changed(self, key, value):
        """Handle SauceOfGrav param slider change."""
        normalized = value / 1000.0
        for param in get_mod_generator_custom_params(self.generator_name):
            if param.get('key') == key:
                real_value = map_value(normalized, param)
                self.parameter_changed.emit(self.slot_id, key, real_value)
                break

    def _on_wave_changed(self, output_idx, wave_index):
        self.output_wave_changed.emit(self.slot_id, output_idx, wave_index)

    def _on_phase_changed(self, output_idx, phase_index):
        self.output_phase_changed.emit(self.slot_id, output_idx, phase_index)

    def _on_polarity_changed(self, output_idx, polarity):
        self.output_polarity_changed.emit(self.slot_id, output_idx, polarity)

    def _on_tension_changed(self, output_idx, value):
        self.tension_changed.emit(self.slot_id, output_idx, value / 1000.0)

    def _on_mass_changed(self, output_idx, value):
        self.mass_changed.emit(self.slot_id, output_idx, value / 1000.0)

    def _on_env_attack_changed(self, env_idx, value):
        self.env_attack_changed.emit(self.slot_id, env_idx, value / 1000.0)

    def _on_env_release_changed(self, env_idx, value):
        self.env_release_changed.emit(self.slot_id, env_idx, value / 1000.0)

    def _on_env_curve_changed(self, env_idx, value):
        self.env_curve_changed.emit(self.slot_id, env_idx, value / 1000.0)

    def _on_env_sync_mode_changed(self, env_idx, mode):
        self.env_sync_mode_changed.emit(self.slot_id, env_idx, mode)

    def _on_env_loop_rate_changed(self, env_idx, rate_idx):
        self.env_loop_rate_changed.emit(self.slot_id, env_idx, rate_idx)

    # =========================================================================
    # State Management
    # =========================================================================

    def get_state(self) -> dict:
        """Get modulator slot state for preset save."""
        params = {}
        for key, widget in self.param_sliders.items():
            if hasattr(widget, 'value'):
                params[key] = widget.value() / 1000.0
            elif hasattr(widget, 'index'):
                params[key] = widget.index

        output_wave = []
        output_phase = []
        output_polarity = []
        output_tension = []
        output_mass = []
        env_attack = []
        env_release = []
        env_curve = []
        env_sync_mode = []
        env_loop_rate = []

        for row_widgets in self.output_rows:
            output_wave.append(row_widgets['wave'].index if 'wave' in row_widgets else 0)
            output_phase.append(row_widgets['phase'].index if 'phase' in row_widgets else 0)
            output_polarity.append(row_widgets['polarity'].index if 'polarity' in row_widgets else 0)
            output_tension.append(row_widgets['tension'].value() / 1000.0 if 'tension' in row_widgets else 0.5)
            output_mass.append(row_widgets['mass'].value() / 1000.0 if 'mass' in row_widgets else 0.5)
            env_attack.append(row_widgets['atk'].value() / 1000.0 if 'atk' in row_widgets else 0.5)
            env_release.append(row_widgets['rel'].value() / 1000.0 if 'rel' in row_widgets else 0.5)
            env_sync_mode.append(row_widgets['sync_mode'].index if 'sync_mode' in row_widgets else 0)

        # Get curve values from _curve_sliders if they exist
        curve_sliders = getattr(self, '_curve_sliders', [])
        env_curve = [s.value() / 1000.0 for s in curve_sliders] if curve_sliders else [0.5] * 4

        # Get loop rate values from _loop_rate_btns if they exist
        loop_rate_btns = getattr(self, '_loop_rate_btns', [])
        env_loop_rate = [b.index for b in loop_rate_btns] if loop_rate_btns else [6] * 4

        # Pad to 4
        for lst, default in [(output_wave, 0), (output_phase, 0), (output_polarity, 0),
                             (output_tension, 0.5), (output_mass, 0.5),
                             (env_attack, 0.5), (env_release, 0.5), (env_curve, 0.5),
                             (env_sync_mode, 0), (env_loop_rate, 6)]:
            while len(lst) < 4:
                lst.append(default)

        return {
            "generator_name": self.generator_name,
            "params": params,
            "output_wave": output_wave[:4],
            "output_phase": output_phase[:4],
            "output_polarity": output_polarity[:4],
            "output_tension": output_tension[:4],
            "output_mass": output_mass[:4],
            "env_attack": env_attack[:4],
            "env_release": env_release[:4],
            "env_curve": env_curve[:4],
            "env_sync_mode": env_sync_mode[:4],
            "env_loop_rate": env_loop_rate[:4],
        }

    def set_state(self, state: dict):
        """Apply modulator slot state from preset load."""
        gen_name = state.get("generator_name", "Empty")
        if gen_name != self.generator_name:
            self.update_for_generator(gen_name)
            if self.gen_button and gen_name in MOD_GENERATOR_CYCLE:
                idx = MOD_GENERATOR_CYCLE.index(gen_name)
                self.gen_button.blockSignals(True)
                self.gen_button.set_index(idx)
                self.gen_button.blockSignals(False)

        # Restore params
        params = state.get("params", {})
        for key, widget in self.param_sliders.items():
            if key in params:
                val = params[key]
                if hasattr(widget, 'setValue'):
                    widget.blockSignals(True)
                    widget.setValue(int(val * 1000) if isinstance(val, float) else val)
                    widget.blockSignals(False)
                elif hasattr(widget, 'set_index'):
                    widget.blockSignals(True)
                    widget.set_index(int(val) if isinstance(val, (int, float)) else 0)
                    widget.blockSignals(False)

        # Restore outputs
        output_wave = state.get("output_wave", [0, 0, 0, 0])
        output_phase = state.get("output_phase", [0, 3, 5, 6])
        output_polarity = state.get("output_polarity", [0, 0, 0, 0])
        output_tension = state.get("output_tension", [0.5, 0.5, 0.5, 0.5])
        output_mass = state.get("output_mass", [0.5, 0.5, 0.5, 0.5])
        env_attack = state.get("env_attack", [0.5, 0.5, 0.5, 0.5])
        env_release = state.get("env_release", [0.5, 0.5, 0.5, 0.5])
        env_curve = state.get("env_curve", [0.5, 0.5, 0.5, 0.5])
        env_sync_mode = state.get("env_sync_mode", [0, 0, 0, 0])
        env_loop_rate = state.get("env_loop_rate", [6, 6, 6, 6])

        for i, row_widgets in enumerate(self.output_rows):
            if i >= 4:
                break

            if 'wave' in row_widgets and i < len(output_wave):
                row_widgets['wave'].blockSignals(True)
                row_widgets['wave'].set_index(output_wave[i])
                row_widgets['wave'].blockSignals(False)

            if 'phase' in row_widgets and i < len(output_phase):
                row_widgets['phase'].blockSignals(True)
                row_widgets['phase'].set_index(output_phase[i])
                row_widgets['phase'].blockSignals(False)

            if 'polarity' in row_widgets and i < len(output_polarity):
                row_widgets['polarity'].blockSignals(True)
                row_widgets['polarity'].set_index(output_polarity[i])
                row_widgets['polarity'].blockSignals(False)

            if 'tension' in row_widgets and output_tension != [0.5, 0.5, 0.5, 0.5]:
                row_widgets['tension'].blockSignals(True)
                row_widgets['tension'].setValue(int(output_tension[i] * 1000))
                row_widgets['tension'].blockSignals(False)

            if 'mass' in row_widgets and output_mass != [0.5, 0.5, 0.5, 0.5]:
                row_widgets['mass'].blockSignals(True)
                row_widgets['mass'].setValue(int(output_mass[i] * 1000))
                row_widgets['mass'].blockSignals(False)

            if 'atk' in row_widgets:
                row_widgets['atk'].blockSignals(True)
                row_widgets['atk'].setValue(int(env_attack[i] * 1000))
                row_widgets['atk'].blockSignals(False)

            if 'rel' in row_widgets:
                row_widgets['rel'].blockSignals(True)
                row_widgets['rel'].setValue(int(env_release[i] * 1000))
                row_widgets['rel'].blockSignals(False)

            if 'sync_mode' in row_widgets:
                row_widgets['sync_mode'].blockSignals(True)
                row_widgets['sync_mode'].set_index(env_sync_mode[i])
                row_widgets['sync_mode'].blockSignals(False)

        # Restore loop rate from _loop_rate_btns
        loop_rate_btns = getattr(self, '_loop_rate_btns', [])
        for i, btn in enumerate(loop_rate_btns):
            if i < len(env_loop_rate):
                btn.blockSignals(True)
                btn.set_index(env_loop_rate[i])
                btn.blockSignals(False)

        self._send_all_state_to_osc()

    def _send_all_state_to_osc(self):
        """Send all current state to SC after preset load."""
        self.generator_changed.emit(self.slot_id, self.generator_name)

        for key, widget in self.param_sliders.items():
            if hasattr(widget, 'value'):
                normalized = widget.value() / 1000.0
                for param in get_mod_generator_custom_params(self.generator_name):
                    if param.get('key') == key:
                        real_value = map_value(normalized, param)
                        self.parameter_changed.emit(self.slot_id, key, real_value)
                        break
            elif hasattr(widget, 'index'):
                self.parameter_changed.emit(self.slot_id, key, float(widget.index))

        for i, row_widgets in enumerate(self.output_rows):
            if 'wave' in row_widgets:
                self.output_wave_changed.emit(self.slot_id, i, row_widgets['wave'].index)
            if 'phase' in row_widgets:
                self.output_phase_changed.emit(self.slot_id, i, row_widgets['phase'].index)
            if 'polarity' in row_widgets:
                self.output_polarity_changed.emit(self.slot_id, i, row_widgets['polarity'].index)
            if 'tension' in row_widgets:
                self.tension_changed.emit(self.slot_id, i, row_widgets['tension'].value() / 1000.0)
            if 'mass' in row_widgets:
                self.mass_changed.emit(self.slot_id, i, row_widgets['mass'].value() / 1000.0)
            if 'atk' in row_widgets:
                self.env_attack_changed.emit(self.slot_id, i, row_widgets['atk'].value() / 1000.0)
            if 'rel' in row_widgets:
                self.env_release_changed.emit(self.slot_id, i, row_widgets['rel'].value() / 1000.0)
            if 'sync_mode' in row_widgets:
                self.env_sync_mode_changed.emit(self.slot_id, i, row_widgets['sync_mode'].index)

        # Emit loop rate from _loop_rate_btns
        loop_rate_btns = getattr(self, '_loop_rate_btns', [])
        for i, btn in enumerate(loop_rate_btns):
            self.env_loop_rate_changed.emit(self.slot_id, i, btn.index)

    def get_param_widget(self, param_index: int):
        """
        Return slider widget for param index (for boid pulse visualization).

        Args:
            param_index: 0-6 (p0-p6)

        Returns:
            Widget with set_boid_glow() method, or None
        """
        # Get all DragSlider widgets from param_sliders (skip CycleButtons)
        sliders = [w for w in self.param_sliders.values()
                   if isinstance(w, DragSlider)]
        if 0 <= param_index < len(sliders):
            return sliders[param_index]
        return None
