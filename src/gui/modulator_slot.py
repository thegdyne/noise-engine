"""
Modulator Slot v2 - Flat absolute positioning
Styled like GeneratorSlot v3 - no builder, all constants at top
"""
from PyQt5.QtWidgets import QWidget, QLabel, QFrame, QSizePolicy
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

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
# LAYOUT - All positions in one place
# =============================================================================
SLOT_LAYOUT = {
    'slot_width': 156,
    'slot_height': 280,

    # Header
    'mod_label_x': 5, 'mod_label_y': 5,
    'mod_label_w': 50, 'mod_label_h': 18,
    'selector_x': 58, 'selector_y': 3,
    'selector_w': 92, 'selector_h': 20,

    # Separator
    'sep_y': 24, 'sep_h': 1,

    # Params area (dynamic)
    'params_y': 28,
    'params_h': 70,
    'slider_w': 18, 'slider_h': 50, 'slider_label_h': 10,
    'mode_btn_w': 28, 'mode_btn_h': 22,

    # Outputs area (dynamic)  
    'outputs_y': 100,
    'output_row_h': 24,
    'output_spacing': 4,
    'output_label_w': 12,
    'wave_btn_w': 40,
    'phase_btn_w': 38,
    'pol_btn_w': 20,
    'slider_h_horiz': 20,

    # Scope
    'scope_x': 4, 'scope_y': 210,
    'scope_w': 148, 'scope_h': 60,
}

L = SLOT_LAYOUT

# Mode labels
MOD_SLOTH_MODES = ["TOR", "APA", "INE"]  # Torpor, Apathy, Inertia
ARSEQ_SYNC_MODES = ["SYN", "LOP"]  # SYNC, LOOP


class ModulatorSlot(QWidget):
    """A single modulator slot with 4 outputs - flat absolute positioning."""

    # Signals
    generator_changed = pyqtSignal(int, str)  # slot_id, generator_name
    parameter_changed = pyqtSignal(int, str, float)  # slot_id, param_key, value
    output_wave_changed = pyqtSignal(int, int, int)  # slot_id, output_idx, wave_index
    output_phase_changed = pyqtSignal(int, int, int)  # slot_id, output_idx, phase_index
    output_polarity_changed = pyqtSignal(int, int, int)  # slot_id, output_idx, invert

    # ARSEq+ envelope signals
    env_attack_changed = pyqtSignal(int, int, float)  # slot_id, env_idx, normalized
    env_release_changed = pyqtSignal(int, int, float)  # slot_id, env_idx, normalized
    env_curve_changed = pyqtSignal(int, int, float)  # slot_id, env_idx, normalized
    env_sync_mode_changed = pyqtSignal(int, int, int)  # slot_id, env_idx, mode
    env_loop_rate_changed = pyqtSignal(int, int, int)  # slot_id, env_idx, rate_idx

    # SauceOfGrav output signals
    tension_changed = pyqtSignal(int, int, float)  # slot_id, output_idx, normalized
    mass_changed = pyqtSignal(int, int, float)  # slot_id, output_idx, normalized

    def __init__(self, slot_id, default_generator="Empty", parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.slot_id = slot_id
        self.setObjectName(f"mod{slot_id}_slot")
        self.default_generator = default_generator
        self.generator_name = "Empty"
        self.output_config = "fixed"

        self.setFixedWidth(L['slot_width'])
        self.setMinimumHeight(L['slot_height'])
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.MinimumExpanding)

        # Storage for dynamic widgets
        self.param_widgets = []  # Cleared on generator change
        self.param_sliders = {}  # key -> widget
        self.output_widgets = []  # Cleared on generator change
        self.output_rows = []  # [{widget_key: widget}, ...]

        self._build_static_ui()
        self.update_for_generator(default_generator)

    # =========================================================================
    # UI Building - Static elements
    # =========================================================================

    def _build_static_ui(self):
        """Build static widgets (header, separator, scope)."""
        # ----- HEADER -----
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

        # ----- SEPARATOR -----
        self.separator = QFrame(self)
        self.separator.setGeometry(4, L['sep_y'], L['slot_width'] - 8, L['sep_h'])
        self.separator.setStyleSheet(f"background-color: {COLORS['border']};")

        # ----- SCOPE -----
        self.scope = ModScope(history_length=100, parent=self)
        self.scope.setGeometry(L['scope_x'], L['scope_y'], L['scope_w'], L['scope_h'])
        self.scope.setStyleSheet(f"border: 1px solid {COLORS['border']}; border-radius: 3px;")

        # Base styling
        self._update_empty_style()

    # =========================================================================
    # UI Building - Dynamic elements  
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

    def _build_params_for_generator(self, gen_name):
        """Build parameter controls for current generator."""
        custom_params = get_mod_generator_custom_params(gen_name)
        if not custom_params:
            return

        x = 6
        for param in custom_params:
            key = param['key']
            steps = param.get('steps')
            try:
                steps_i = int(steps) if steps is not None else None
            except (ValueError, TypeError):
                steps_i = None

            is_mode_btn = key in ('mode', 'clock_mode') and steps_i in (2, 3)

            if is_mode_btn:
                x = self._build_mode_button(x, param, key, steps_i)
            else:
                x = self._build_param_slider(x, param, key)

    def _build_mode_button(self, x, param, key, steps_i):
        """Build a mode CycleButton at x position."""
        y = L['params_y']

        # Determine mode labels
        if key == 'clock_mode':
            mode_labels = MOD_LFO_MODES
            tooltip = "CLK: sync to transport\nFREE: free-running rate"
        elif key == 'mode' and self.generator_name == "ARSEq+":
            mode_labels = ["SEQ", "PAR"]
            tooltip = "SEQ: envelopes fire in sequence\nPAR: all fire together"
        elif steps_i == 2:
            mode_labels = MOD_LFO_MODES
            tooltip = "CLK: sync to clock divisions\nFREE: manual frequency"
        else:
            mode_labels = MOD_SLOTH_MODES
            tooltip = "Torpor: 15-30s\nApathy: 60-90s\nInertia: 30-40min"

        default_idx = int(round(float(param.get('default', 0.0))))
        default_idx = max(0, min(default_idx, steps_i - 1))

        # Label
        label_text = param.get('label_top', param.get('label', key.upper()[:4]))
        lbl = QLabel(label_text, self)
        lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(f"color: {COLORS['text']};")
        lbl.setGeometry(x, y, L['mode_btn_w'], L['slider_label_h'])
        self.param_widgets.append(lbl)

        # Button
        btn = CycleButton(mode_labels, initial_index=default_idx, parent=self)
        btn.setGeometry(x, y + L['slider_label_h'] + 2, L['mode_btn_w'], L['mode_btn_h'])
        btn.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        btn.setStyleSheet(button_style('submenu'))
        btn.setToolTip(tooltip)
        btn.text_alignment = Qt.AlignVCenter | Qt.AlignHCenter
        btn.index_changed.connect(lambda idx, k=key: self._on_mode_changed(k, idx))
        self.param_widgets.append(btn)
        self.param_sliders[key] = btn

        return x + L['mode_btn_w'] + 4

    def _build_param_slider(self, x, param, key):
        """Build a DragSlider at x position."""
        y = L['params_y']

        # Label
        label_text = param.get('label_top', param.get('label', key.upper()[:4]))
        lbl = QLabel(label_text, self)
        lbl.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(f"color: {COLORS['text']};")
        lbl.setGeometry(x, y, L['slider_w'], L['slider_label_h'])
        lbl.setToolTip(param.get('tooltip', ''))
        self.param_widgets.append(lbl)

        # Slider
        slider = DragSlider(parent=self)
        slider.setRange(0, 1000)
        slider.setGeometry(x, y + L['slider_label_h'], L['slider_w'], L['slider_h'])
        default_val = float(param.get('default', 0.5))
        slider.setValue(int(default_val * 1000))
        slider.setToolTip(param.get('tooltip', ''))

        if param.get('bipolar', False):
            slider.setDoubleClickValue(500)

        slider.valueChanged.connect(lambda v, k=key, p=param: self._on_param_changed(k, v, p))
        self.param_widgets.append(slider)
        self.param_sliders[key] = slider

        return x + L['slider_w'] + 4

    def _build_outputs_for_generator(self, gen_name):
        """Build output rows for current generator."""
        output_labels = get_mod_output_labels(gen_name)
        output_config = get_mod_generator_output_config(gen_name)

        y = L['outputs_y']
        for i in range(MOD_OUTPUTS_PER_SLOT):
            label = output_labels[i] if i < len(output_labels) else str(i + 1)

            if gen_name == "ARSEq+":
                row_widgets = self._build_arseq_output_row(i, y, label)
            elif gen_name == "SauceOfGrav":
                row_widgets = self._build_saucegrav_output_row(i, y, label)
            else:
                row_widgets = self._build_lfo_output_row(i, y, label, output_config)

            self.output_rows.append(row_widgets)
            y += L['output_row_h'] + L['output_spacing']

    def _build_lfo_output_row(self, idx, y, label, output_config):
        """Build LFO/Sloth output row at y position."""
        row_widgets = {}
        x = 6

        # Output label
        lbl = QLabel(label, self)
        lbl.setFont(QFont(MONO_FONT, FONT_SIZES['small'], QFont.Bold))
        lbl.setStyleSheet(f"color: {COLORS['text_bright']};")
        lbl.setGeometry(x, y, L['output_label_w'], L['output_row_h'])
        self.output_widgets.append(lbl)
        row_widgets['label'] = lbl
        x += L['output_label_w'] + 4

        # Waveform button (for LFO types)
        if output_config in ("waveform_phase", "pattern_rotate"):
            wave_btn = CycleButton(MOD_LFO_WAVEFORMS, initial_index=0, parent=self)
            wave_btn.setGeometry(x, y, L['wave_btn_w'], L['output_row_h'] - 2)
            wave_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
            wave_btn.setStyleSheet(button_style('submenu'))
            wave_btn.setToolTip("Waveform: Saw/Tri/Sqr/Sin/S&H")
            wave_btn.text_alignment = Qt.AlignVCenter | Qt.AlignHCenter
            wave_btn.value_changed.connect(
                lambda w, i=idx: self._on_wave_changed(i, MOD_LFO_WAVEFORMS.index(w))
            )
            self.output_widgets.append(wave_btn)
            row_widgets['wave'] = wave_btn
            x += L['wave_btn_w'] + 2

            # Phase button (only for waveform_phase)
            if output_config == "waveform_phase":
                default_phases = [0, 3, 5, 6]
                phase_labels = [f"{p}°" for p in MOD_LFO_PHASES]
                phase_btn = CycleButton(phase_labels,
                                        initial_index=default_phases[idx] if idx < 4 else 0,
                                        parent=self)
                phase_btn.setGeometry(x, y, L['phase_btn_w'], L['output_row_h'] - 2)
                phase_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
                phase_btn.setStyleSheet(button_style('submenu'))
                phase_btn.setToolTip("Phase offset: 0°-315° in 45° steps")
                phase_btn.text_alignment = Qt.AlignVCenter | Qt.AlignHCenter
                phase_btn.value_changed.connect(
                    lambda p, i=idx, pl=phase_labels: self._on_phase_changed(i, pl.index(p))
                )
                self.output_widgets.append(phase_btn)
                row_widgets['phase'] = phase_btn
                x += L['phase_btn_w'] + 2

        # Polarity button (always present)
        pol_btn = CycleButton(MOD_POLARITY, initial_index=0, parent=self)
        pol_btn.setGeometry(x, y, L['pol_btn_w'], L['output_row_h'] - 2)
        pol_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        pol_btn.setStyleSheet(button_style('submenu'))
        pol_btn.setToolTip("Invert: NORM/INV")
        pol_btn.text_alignment = Qt.AlignVCenter | Qt.AlignHCenter
        pol_btn.value_changed.connect(
            lambda p, i=idx: self._on_polarity_changed(i, MOD_POLARITY.index(p))
        )
        self.output_widgets.append(pol_btn)
        row_widgets['polarity'] = pol_btn

        return row_widgets

    def _build_arseq_output_row(self, idx, y, label):
        """Build ARSEq+ envelope output row at y position."""
        row_widgets = {}
        x = 6

        # Output label
        lbl = QLabel(label, self)
        lbl.setFont(QFont(MONO_FONT, FONT_SIZES['small'], QFont.Bold))
        lbl.setStyleSheet(f"color: {COLORS['text_bright']};")
        lbl.setGeometry(x, y, L['output_label_w'], L['output_row_h'])
        self.output_widgets.append(lbl)
        row_widgets['label'] = lbl
        x += L['output_label_w'] + 2

        # ATK slider (horizontal)
        atk = DragSlider(parent=self)
        atk.setRange(0, 1000)
        atk.setOrientation(Qt.Horizontal)
        atk.setGeometry(x, y + 2, 34, L['slider_h_horiz'])
        atk.setValue(0)
        atk.setToolTip("ATK")
        atk.valueChanged.connect(lambda v, i=idx: self._on_env_attack_changed(i, v))
        self.output_widgets.append(atk)
        row_widgets['atk'] = atk
        x += 36

        # REL slider (horizontal)
        rel = DragSlider(parent=self)
        rel.setRange(0, 1000)
        rel.setOrientation(Qt.Horizontal)
        rel.setGeometry(x, y + 2, 34, L['slider_h_horiz'])
        rel.setValue(500)
        rel.setToolTip("REL")
        rel.valueChanged.connect(lambda v, i=idx: self._on_env_release_changed(i, v))
        self.output_widgets.append(rel)
        row_widgets['rel'] = rel
        x += 36

        # Hidden curve slider (for preset save/load)
        crv = DragSlider(parent=self)
        crv.setRange(0, 1000)
        crv.setValue(500)
        crv.setVisible(False)
        crv.valueChanged.connect(lambda v, i=idx: self._on_env_curve_changed(i, v))
        self.output_widgets.append(crv)
        row_widgets['curve'] = crv

        # Sync mode button
        sync_btn = CycleButton(ARSEQ_SYNC_MODES, initial_index=0, parent=self)
        sync_btn.setGeometry(x, y, 28, L['output_row_h'] - 2)
        sync_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        sync_btn.setStyleSheet(button_style('submenu'))
        sync_btn.setToolTip("SYN: master / LOP: loop")
        sync_btn.text_alignment = Qt.AlignVCenter | Qt.AlignHCenter
        sync_btn.index_changed.connect(lambda m, i=idx: self._on_env_sync_mode_changed(i, m))
        self.output_widgets.append(sync_btn)
        row_widgets['sync_mode'] = sync_btn
        x += 30

        # Loop rate button (hidden by default)
        loop_btn = CycleButton(MOD_CLOCK_RATES, initial_index=6, parent=self)
        loop_btn.setGeometry(x - 30, y, 28, L['output_row_h'] - 2)
        loop_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        loop_btn.setStyleSheet(button_style('submenu'))
        loop_btn.setToolTip("Loop rate")
        loop_btn.setVisible(False)
        loop_btn.index_changed.connect(lambda r, i=idx: self._on_env_loop_rate_changed(i, r))
        self.output_widgets.append(loop_btn)
        row_widgets['loop_rate'] = loop_btn

        # Shift+click toggles rate visibility
        def toggle_rate(s=sync_btn, r=loop_btn):
            if s.index == 1:  # LOP mode
                r.setVisible(not r.isVisible())
                s.setVisible(not r.isVisible())
        sync_btn.shift_click_callback = toggle_rate
        loop_btn.shift_click_callback = toggle_rate

        # Polarity button
        pol_btn = CycleButton(MOD_POLARITY, initial_index=0, parent=self)
        pol_btn.setGeometry(x, y, L['pol_btn_w'], L['output_row_h'] - 2)
        pol_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        pol_btn.setStyleSheet(button_style('submenu'))
        pol_btn.setToolTip("N/I")
        pol_btn.text_alignment = Qt.AlignVCenter | Qt.AlignHCenter
        pol_btn.value_changed.connect(
            lambda p, i=idx: self._on_polarity_changed(i, MOD_POLARITY.index(p))
        )
        self.output_widgets.append(pol_btn)
        row_widgets['polarity'] = pol_btn

        return row_widgets

    def _build_saucegrav_output_row(self, idx, y, label):
        """Build SauceOfGrav output row at y position."""
        row_widgets = {}
        x = 6

        # Output label
        lbl = QLabel(label, self)
        lbl.setFont(QFont(MONO_FONT, FONT_SIZES['small'], QFont.Bold))
        lbl.setStyleSheet(f"color: {COLORS['text_bright']};")
        lbl.setGeometry(x, y, L['output_label_w'], L['output_row_h'])
        self.output_widgets.append(lbl)
        row_widgets['label'] = lbl
        x += L['output_label_w'] + 2

        # TENS slider (horizontal)
        tension_defaults = [300, 450, 550, 700]
        tens = DragSlider(parent=self)
        tens.setRange(0, 1000)
        tens.setOrientation(Qt.Horizontal)
        tens.setGeometry(x, y + 2, 45, L['slider_h_horiz'])
        tens.setValue(tension_defaults[idx] if idx < 4 else 500)
        tens.setToolTip("TENS: low=independent, high=coupled")
        tens.valueChanged.connect(lambda v, i=idx: self._on_tension_changed(i, v))
        self.output_widgets.append(tens)
        row_widgets['tension'] = tens
        x += 47

        # MASS slider (horizontal)
        mass_defaults = [650, 550, 450, 350]
        mass = DragSlider(parent=self)
        mass.setRange(0, 1000)
        mass.setOrientation(Qt.Horizontal)
        mass.setGeometry(x, y + 2, 45, L['slider_h_horiz'])
        mass.setValue(mass_defaults[idx] if idx < 4 else 500)
        mass.setToolTip("MASS: low=snappy, high=slow arcs")
        mass.valueChanged.connect(lambda v, i=idx: self._on_mass_changed(i, v))
        self.output_widgets.append(mass)
        row_widgets['mass'] = mass
        x += 47

        # Polarity button
        pol_btn = CycleButton(MOD_POLARITY, initial_index=0, parent=self)
        pol_btn.setGeometry(x, y, L['pol_btn_w'], L['output_row_h'] - 2)
        pol_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        pol_btn.setStyleSheet(button_style('submenu'))
        pol_btn.setToolTip("N/I")
        pol_btn.text_alignment = Qt.AlignVCenter | Qt.AlignHCenter
        pol_btn.value_changed.connect(
            lambda p, i=idx: self._on_polarity_changed(i, MOD_POLARITY.index(p))
        )
        self.output_widgets.append(pol_btn)
        row_widgets['polarity'] = pol_btn

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

        # Clear dynamic widgets
        self._clear_dynamic_widgets()

        if gen_name == "Empty":
            self._setup_empty_state()
            return

        # Build params and outputs
        self._build_params_for_generator(gen_name)
        self._build_outputs_for_generator(gen_name)
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
    # Event Handlers
    # =========================================================================

    def _on_mode_changed(self, key, index):
        """Handle mode button change."""
        self.parameter_changed.emit(self.slot_id, key, float(index))

    def _on_param_changed(self, key, slider_value, param):
        """Handle parameter slider change."""
        normalized = slider_value / 1000.0
        real_value = map_value(normalized, param)

        # Show drag popup with formatted value
        slider = self.param_sliders.get(key)
        if slider and hasattr(slider, 'show_drag_value'):
            display_text = self._format_param_value(key, normalized, real_value)
            if display_text:
                slider.show_drag_value(display_text)

        self.parameter_changed.emit(self.slot_id, key, real_value)

    def _format_param_value(self, key, normalized, real_value):
        """Format parameter value for drag popup display."""
        if key == 'rate':
            mode_btn = self.param_sliders.get('mode')
            mode = mode_btn.index if mode_btn and hasattr(mode_btn, 'index') else 0

            if mode == 0:  # CLK mode
                rate_idx = int(normalized * (len(MOD_CLOCK_RATES) - 1))
                rate_idx = max(0, min(rate_idx, len(MOD_CLOCK_RATES) - 1))
                return MOD_CLOCK_RATES[rate_idx]
            else:  # FREE mode
                import math
                freq = MOD_LFO_FREQ_MIN * math.pow(MOD_LFO_FREQ_MAX / MOD_LFO_FREQ_MIN, normalized)
                if freq < 1:
                    return f"{freq:.2f}Hz"
                elif freq < 10:
                    return f"{freq:.1f}Hz"
                else:
                    return f"{freq:.0f}Hz"

        return f"{int(normalized * 100)}%"

    def _on_wave_changed(self, output_idx, wave_index):
        """Handle waveform change."""
        self.output_wave_changed.emit(self.slot_id, output_idx, wave_index)

    def _on_phase_changed(self, output_idx, phase_index):
        """Handle phase change."""
        self.output_phase_changed.emit(self.slot_id, output_idx, phase_index)

    def _on_polarity_changed(self, output_idx, polarity):
        """Handle polarity change."""
        self.output_polarity_changed.emit(self.slot_id, output_idx, polarity)

    def _on_tension_changed(self, output_idx, value):
        """Handle tension slider change."""
        self.tension_changed.emit(self.slot_id, output_idx, value / 1000.0)

    def _on_mass_changed(self, output_idx, value):
        """Handle mass slider change."""
        self.mass_changed.emit(self.slot_id, output_idx, value / 1000.0)

    def _on_env_attack_changed(self, env_idx, value):
        """Handle ARSEq+ envelope attack change."""
        self.env_attack_changed.emit(self.slot_id, env_idx, value / 1000.0)

    def _on_env_release_changed(self, env_idx, value):
        """Handle ARSEq+ envelope release change."""
        self.env_release_changed.emit(self.slot_id, env_idx, value / 1000.0)

    def _on_env_curve_changed(self, env_idx, value):
        """Handle ARSEq+ envelope curve change."""
        self.env_curve_changed.emit(self.slot_id, env_idx, value / 1000.0)

    def _on_env_sync_mode_changed(self, env_idx, mode):
        """Handle ARSEq+ envelope sync mode change."""
        self.env_sync_mode_changed.emit(self.slot_id, env_idx, mode)

    def _on_env_loop_rate_changed(self, env_idx, rate_idx):
        """Handle ARSEq+ envelope loop rate change."""
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
            env_curve.append(row_widgets['curve'].value() / 1000.0 if 'curve' in row_widgets else 0.5)
            env_sync_mode.append(row_widgets['sync_mode'].index if 'sync_mode' in row_widgets else 0)
            env_loop_rate.append(row_widgets['loop_rate'].index if 'loop_rate' in row_widgets else 6)

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

            if 'curve' in row_widgets:
                row_widgets['curve'].blockSignals(True)
                row_widgets['curve'].setValue(int(env_curve[i] * 1000))
                row_widgets['curve'].blockSignals(False)

            if 'sync_mode' in row_widgets:
                row_widgets['sync_mode'].blockSignals(True)
                row_widgets['sync_mode'].set_index(env_sync_mode[i])
                row_widgets['sync_mode'].blockSignals(False)

            if 'loop_rate' in row_widgets:
                row_widgets['loop_rate'].blockSignals(True)
                row_widgets['loop_rate'].set_index(env_loop_rate[i])
                row_widgets['loop_rate'].blockSignals(False)

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
            if 'curve' in row_widgets:
                self.env_curve_changed.emit(self.slot_id, i, row_widgets['curve'].value() / 1000.0)
            if 'sync_mode' in row_widgets:
                self.env_sync_mode_changed.emit(self.slot_id, i, row_widgets['sync_mode'].index)
            if 'loop_rate' in row_widgets:
                self.env_loop_rate_changed.emit(self.slot_id, i, row_widgets['loop_rate'].index)
