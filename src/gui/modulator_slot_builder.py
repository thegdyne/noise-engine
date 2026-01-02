"""
Modulator Slot UI Builder
Handles layout construction for ModulatorSlot

Hierarchy:
- ModulatorHeader
- ModulatorFrame
  - ModulatorSliderSection
  - ModulatorOutputSection
- ModulatorScope
"""

from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QFrame, QWidget, QSizePolicy
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from .theme import COLORS, button_style, MONO_FONT, FONT_FAMILY, FONT_SIZES, MODULATOR_THEME
from .widgets import CycleButton, DragSlider
from src.config import (
    MOD_GENERATOR_CYCLE,
    MOD_LFO_WAVEFORMS,
    MOD_LFO_PHASES,
    MOD_LFO_MODES,
    MOD_POLARITY,
    MOD_OUTPUTS_PER_SLOT,
    SIZES,
)

# Sloth mode labels (must match steps: 3 in sloth.json)
MOD_SLOTH_MODES = ["TOR", "APA", "INE"]  # Torpor, Apathy, Inertia


class EnvelopeIndicator(QWidget):
    """Visual indicator showing envelope fill/drain state."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0.0  # 0-1 fill level
        self._phase = 'idle'  # 'attack', 'release', 'idle'
        self._curve = 0.5  # 0=log, 0.5=lin, 1=exp

    def setValue(self, value):
        """Set fill level (0-1)."""
        self._value = max(0.0, min(1.0, value))
        self.update()

    def setPhase(self, phase):
        """Set phase: 'attack', 'release', or 'idle'."""
        self._phase = phase
        self.update()

    def setCurve(self, curve):
        """Set curve shape (0=log, 0.5=lin, 1=exp)."""
        self._curve = curve
        self.update()

    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QColor
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor(COLORS['background_dark']))

        # Fill bar
        if self._value > 0:
            fill_color = QColor(COLORS.get('accent_mod_arseq_plus', '#00CCCC'))
            fill_w = int(w * self._value)
            if self._phase == 'release':
                painter.fillRect(w - fill_w, 0, fill_w, h, fill_color)
            else:
                painter.fillRect(0, 0, fill_w, h, fill_color)

        # Center line
        painter.setPen(QColor(COLORS['border_light']))
        painter.drawLine(w // 2, 0, w // 2, h)

        painter.end()


def build_modulator_header(slot):
    """Build the header row with slot ID and generator selector."""
    mt = MODULATOR_THEME
    header = QHBoxLayout()
    header.setSpacing(mt['header_spacing'])
    
    # Slot number
    slot.id_label = QLabel(f"MOD {slot.slot_id}")
    slot.id_label.setObjectName(f"mod{slot.slot_id}_label")
    slot.id_label.setFont(QFont(FONT_FAMILY, FONT_SIZES['small'], QFont.Bold))
    slot.id_label.setStyleSheet(f"color: {COLORS['text_bright']};")
    header.addWidget(slot.id_label)
    
    header.addStretch()
    
    # Generator selector button
    initial_idx = MOD_GENERATOR_CYCLE.index(slot.default_generator) if slot.default_generator in MOD_GENERATOR_CYCLE else 0
    slot.gen_button = CycleButton(MOD_GENERATOR_CYCLE, initial_index=initial_idx)
    slot.gen_button.setObjectName(f"mod{slot.slot_id}_type")
    slot.gen_button.setFixedSize(mt['header_button_width'], mt['header_button_height'])
    slot.gen_button.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
    slot.gen_button.setStyleSheet(button_style('submenu'))
    # Left-align text with padding
    slot.gen_button.text_alignment = Qt.AlignVCenter | Qt.AlignLeft
    slot.gen_button.text_padding_lr = 4
    slot.gen_button.value_changed.connect(slot._on_generator_changed)
    header.addWidget(slot.gen_button)
    
    return header


def build_modulator_separator():
    """Build a horizontal separator line."""
    sep = QFrame()
    sep.setFrameShape(QFrame.HLine)
    sep.setStyleSheet(f"background-color: {COLORS['border']};")
    sep.setFixedHeight(1)
    return sep


def build_modulator_slider_section(slot):
    """Build the parameters container."""
    mt = MODULATOR_THEME
    slot.params_container = QWidget()
    slot.params_layout = QHBoxLayout(slot.params_container)
    m = mt['slider_section_margins']
    slot.params_layout.setContentsMargins(m[0], m[1], m[2], m[3])
    slot.params_layout.setSpacing(0)
    return slot.params_container


def build_modulator_output_section(slot):
    """Build the outputs container."""
    slot.outputs_container = QWidget()
    slot.outputs_layout = QVBoxLayout(slot.outputs_container)
    slot.outputs_layout.setContentsMargins(0, 0, 0, 0)
    slot.outputs_layout.setSpacing(4)
    return slot.outputs_container


def build_modulator_scope(slot):
    """Build the oscilloscope display."""
    from .mod_scope import ModScope
    mt = MODULATOR_THEME
    slot.scope = ModScope(history_length=100)
    slot.scope.setObjectName(f"mod{slot.slot_id}_scope")
    slot.scope.setFixedHeight(mt['scope_height'])
    slot.scope.setStyleSheet(f"""
        border: 1px solid {COLORS['border']};
        border-radius: 3px;
    """)
    return slot.scope


def build_param_slider(slot, param):
    """Build a parameter control - CycleButton for mode, DragSlider for continuous."""
    mt = MODULATOR_THEME
    
    key = param['key']
    steps = param.get('steps')
    try:
        steps_i = int(steps) if steps is not None else None
    except (ValueError, TypeError):
        steps_i = None

    # Mode buttons need wider column
    is_mode_btn = key in ('mode', 'clock_mode') and steps_i in (2, 3)
    col_width = 28 if is_mode_btn else 20
    
    # Fixed-width column widget
    col = QWidget()
    col.setFixedWidth(col_width)
    col.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
    
    container = QVBoxLayout(col)
    container.setContentsMargins(0, 0, 0, 0)
    container.setSpacing(1)

    # Label - only show if no label_top (SauceOfGrav uses top/bottom labels instead)
    if not param.get('label_top'):
        label = QLabel(param.get('label', key.upper()[:4]))
        label.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(f"color: {COLORS['text']};")
        label.setToolTip(param.get('tooltip', ''))
        label.setFixedHeight(mt['param_label_height'])
        label.setFixedWidth(col_width)
        label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        container.addWidget(label)

    # Use CycleButton for stepped params
    if is_mode_btn:
        if key == 'clock_mode':
            # ARSEq+ clock mode: CLK/FREE
            mode_labels = MOD_LFO_MODES  # Reuse CLK/FREE
            tooltip = "CLK: sync to transport\nFREE: free-running rate"
        elif key == 'mode' and slot.generator_name == "ARSEq+":
            # ARSEq+ mode: SEQ/PAR
            mode_labels = ["SEQ", "PAR"]
            tooltip = "SEQ: envelopes fire in sequence (1→2→3→4)\nPAR: all fire together"
        elif steps_i == 2:
            # LFO mode: CLK/FREE
            mode_labels = MOD_LFO_MODES
            tooltip = "CLK: sync to clock divisions\nFREE: manual frequency (0.01-100Hz)"
        else:
            # Sloth mode: Torpor/Apathy/Inertia
            mode_labels = MOD_SLOTH_MODES
            tooltip = "Torpor: 15-30s\nApathy: 60-90s\nInertia: 30-40min"
        
        # Respect JSON default
        default_idx = int(round(float(param.get('default', 0.0))))
        default_idx = max(0, min(default_idx, steps_i - 1))
        
        btn = CycleButton(mode_labels, initial_index=default_idx)
        btn.setObjectName(f"mod{slot.slot_id}_mode")
        # Mode buttons need specific width to show text like "CLK", "FREE"
        btn.setFixedSize(28, 22)
        btn.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        btn.setStyleSheet(button_style('submenu'))
        btn.setToolTip(tooltip)
        btn.text_alignment = Qt.AlignVCenter | Qt.AlignHCenter
        btn.text_padding_lr = 2
        btn.index_changed.connect(
            lambda idx, k=key: slot._on_mode_changed(k, idx)
        )
        container.addWidget(btn)
        return col

    # Add top label (for sliders with label_top specified)
    label_top = param.get('label_top', '')
    top_label = QLabel(label_top)
    top_label.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
    top_label.setAlignment(Qt.AlignCenter)
    top_label.setStyleSheet(f"color: {COLORS['text']};")
    top_label.setFixedHeight(mt['param_label_height'])
    top_label.setFixedWidth(col_width)
    top_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    container.addWidget(top_label)

    # DragSlider for continuous params
    slider = DragSlider()
    slider.setObjectName(f"mod{slot.slot_id}_{key}")
    slider.setFixedSize(18, mt['slider_height'])

    # Bipolar params show center notch
    is_bipolar = param.get('bipolar', False)

    # Set default value
    default_val = float(param.get('default', 0.5))
    slider.setValue(int(default_val * 1000))

    # Bipolar params: double-click resets to center
    if is_bipolar:
        slider.setDoubleClickValue(500)

    # Connect value change
    slider.valueChanged.connect(
        lambda val, k=key, p=param: slot._on_param_changed(k, val, p)
    )

    slider.setToolTip(param.get('tooltip', ''))
    container.addWidget(slider, alignment=Qt.AlignHCenter)

    # Add bottom label (for alignment; shows text if label_bottom specified)
    label_bottom = param.get('label_bottom', '')
    bottom_label = QLabel(label_bottom)
    bottom_label.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
    bottom_label.setAlignment(Qt.AlignCenter)
    bottom_label.setStyleSheet(f"color: {COLORS['text']};")
    bottom_label.setFixedHeight(mt['param_label_height'])
    bottom_label.setFixedWidth(col_width)
    bottom_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    container.addWidget(bottom_label)

    return col


def build_output_row(slot, output_idx, label, output_config):
    """Build a single output row with waveform, phase, and polarity controls."""
    mt = MODULATOR_THEME
    row = QHBoxLayout()
    row.setSpacing(4)
    row.setContentsMargins(0, 0, 0, 0)
    
    # Output label
    out_label = QLabel(label)
    out_label.setFont(QFont(MONO_FONT, FONT_SIZES['small'], QFont.Bold))
    out_label.setStyleSheet(f"color: {COLORS['text_bright']};")
    out_label.setFixedWidth(mt['output_label_width'])
    out_label.setToolTip(f"Output {label}: route to mod matrix")
    row.addWidget(out_label)
    
    row_widgets = {'label': out_label}
    
    btn_height = mt.get('output_button_height', 20)
    
    if output_config in ("waveform_phase", "pattern_rotate"):
        # LFO: waveform + polarity per output
        # pattern_rotate: phases controlled globally via PAT/ROT params
        wave_btn = CycleButton(MOD_LFO_WAVEFORMS, initial_index=0)
        wave_btn.setObjectName(f"mod{slot.slot_id}_wave{output_idx}")
        wave_btn.setFixedSize(mt.get('wave_button_width', 40), btn_height)
        wave_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        wave_btn.setStyleSheet(button_style('submenu'))
        wave_btn.setToolTip("Waveform: Saw/Tri/Sqr/Sin/S&H")
        wave_btn.text_alignment = Qt.AlignVCenter | Qt.AlignHCenter
        wave_btn.text_padding_lr = 2
        wave_btn.value_changed.connect(
            lambda w, idx=output_idx, wforms=MOD_LFO_WAVEFORMS: slot._on_wave_changed(idx, wforms.index(w))
        )

        if output_idx == 0:
            wave_container = QVBoxLayout()
            wave_container.setSpacing(2)
            wave_container.setContentsMargins(0, 0, 0, 0)
            wave_label = QLabel("SHAPE")
            wave_label.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
            wave_label.setAlignment(Qt.AlignCenter)
            wave_label.setStyleSheet(f"color: {COLORS['text']};")
            wave_container.addWidget(wave_label)
            wave_container.addWidget(wave_btn)
            row.addLayout(wave_container)
        else:
            row.addWidget(wave_btn)
        row_widgets['wave'] = wave_btn
        
        # Only add per-output phase for old "waveform_phase" config (backward compat)
        if output_config == "waveform_phase":
            # Default phases: A=0° (idx 0), B=135° (idx 3), C=225° (idx 5)
            default_phase_indices = [0, 3, 5, 6]  # 4 outputs now
            phase_labels = [f"{p}°" for p in MOD_LFO_PHASES]
            phase_btn = CycleButton(phase_labels, initial_index=default_phase_indices[output_idx] if output_idx < len(default_phase_indices) else 0)
            phase_btn.setObjectName(f"mod{slot.slot_id}_phase{output_idx}")
            phase_btn.setFixedSize(mt.get('phase_button_width', 38), btn_height)
            phase_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
            phase_btn.setStyleSheet(button_style('submenu'))
            phase_btn.setToolTip("Phase offset: 0°-315° in 45° steps")
            phase_btn.text_alignment = Qt.AlignVCenter | Qt.AlignHCenter
            phase_btn.text_padding_lr = 2
            phase_btn.value_changed.connect(
                lambda p, idx=output_idx, plabels=phase_labels: slot._on_phase_changed(idx, plabels.index(p))
            )
            row.addWidget(phase_btn)
            row_widgets['phase'] = phase_btn

    elif output_config == "arseq_plus":
        # ARSEq+ uses dedicated row builder
        return build_arseq_output_row(slot, output_idx, label)

    elif output_config == "sauce_of_grav":
        # SauceOfGrav uses dedicated row builder
        return build_saucegrav_output_row(slot, output_idx, label)

    # Polarity button (all generators)
    # Default: NORM (non-inverted) for all outputs
    default_polarity = 0  # NORM by default
    pol_btn = CycleButton(MOD_POLARITY, initial_index=default_polarity)
    pol_btn.setObjectName(f"mod{slot.slot_id}_pol{output_idx}")
    pol_btn.setFixedSize(mt.get('pol_button_width', 28), btn_height)
    pol_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
    pol_btn.setStyleSheet(button_style('submenu'))
    pol_btn.setToolTip("Invert: NORM (original) / INV (flipped)")
    pol_btn.text_alignment = Qt.AlignVCenter | Qt.AlignHCenter
    pol_btn.text_padding_lr = 2
    pol_btn.value_changed.connect(
        lambda p, idx=output_idx, pols=MOD_POLARITY: slot._on_polarity_changed(idx, pols.index(p))
    )

    if output_idx == 0:
        pol_container = QVBoxLayout()
        pol_container.setSpacing(2)
        pol_container.setContentsMargins(0, 0, 0, 0)
        pol_label = QLabel("INV")
        pol_label.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        pol_label.setAlignment(Qt.AlignCenter)
        pol_label.setStyleSheet(f"color: {COLORS['text']};")
        pol_container.addWidget(pol_label)
        pol_container.addWidget(pol_btn)
        row.addLayout(pol_container)
    else:
        row.addWidget(pol_btn)
    row_widgets['polarity'] = pol_btn
    
    row.addStretch()
    
    return row, row_widgets


# ARSEq+ sync/loop mode labels
ARSEQ_SYNC_MODES = ["SYN", "LOP"]  # SYNC, LOOP

def build_arseq_output_row(slot, output_idx, label):
    """Build an ARSEq+ envelope output row - minimal horizontal."""
    mt = MODULATOR_THEME
    row = QHBoxLayout()
    row.setSpacing(4)
    row.setContentsMargins(0, 0, 0, 0)

    row_widgets = {}
    btn_height = 20

    # Output label (envelope number)
    out_label = QLabel(label)
    out_label.setFont(QFont(MONO_FONT, FONT_SIZES['small'], QFont.Bold))
    out_label.setStyleSheet(f"color: {COLORS['text_bright']};")
    out_label.setFixedWidth(12)
    out_label.setToolTip(f"Envelope {label}")
    row.addWidget(out_label)
    row_widgets['label'] = out_label

    # ATK slider (horizontal, wider) - with label on first row
    atk_slider = DragSlider()
    atk_slider.setObjectName(f"mod{slot.slot_id}_env{output_idx}_atk")
    atk_slider.setFixedHeight(btn_height)
    atk_slider.setMinimumWidth(30)
    atk_slider.setOrientation(Qt.Horizontal)
    atk_slider.setValue(0)
    atk_slider.setToolTip("ATK")
    atk_slider.valueChanged.connect(
        lambda val, idx=output_idx: slot._on_env_attack_changed(idx, val)
    )

    if output_idx == 0:
        atk_container = QVBoxLayout()
        atk_container.setSpacing(2)
        atk_container.setContentsMargins(0, 0, 0, 0)
        atk_label = QLabel("ATK")
        atk_label.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        atk_label.setAlignment(Qt.AlignCenter)
        atk_label.setStyleSheet(f"color: {COLORS['text']};")
        atk_container.addWidget(atk_label)
        atk_container.addWidget(atk_slider)
        row.addLayout(atk_container, 1)
    else:
        row.addWidget(atk_slider, 1)
    row_widgets['atk'] = atk_slider

    # REL slider (horizontal, wider) - with label on first row
    rel_slider = DragSlider()
    rel_slider.setObjectName(f"mod{slot.slot_id}_env{output_idx}_rel")
    rel_slider.setFixedHeight(btn_height)
    rel_slider.setMinimumWidth(30)
    rel_slider.setOrientation(Qt.Horizontal)
    rel_slider.setValue(500)
    rel_slider.setToolTip("REL")
    rel_slider.valueChanged.connect(
        lambda val, idx=output_idx: slot._on_env_release_changed(idx, val)
    )

    if output_idx == 0:
        rel_container = QVBoxLayout()
        rel_container.setSpacing(2)
        rel_container.setContentsMargins(0, 0, 0, 0)
        rel_label = QLabel("REL")
        rel_label.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        rel_label.setAlignment(Qt.AlignCenter)
        rel_label.setStyleSheet(f"color: {COLORS['text']};")
        rel_container.addWidget(rel_label)
        rel_container.addWidget(rel_slider)
        row.addLayout(rel_container, 1)
    else:
        row.addWidget(rel_slider, 1)
    row_widgets['rel'] = rel_slider

    # Hidden curve slider (stored but not shown - simplify UI)
    crv_slider = DragSlider()
    crv_slider.setObjectName(f"mod{slot.slot_id}_env{output_idx}_crv")
    crv_slider.setValue(500)
    crv_slider.setVisible(False)
    crv_slider.valueChanged.connect(
        lambda val, idx=output_idx: slot._on_env_curve_changed(idx, val)
    )
    row_widgets['curve'] = crv_slider

    # LOOP rate selector (created first, hidden by default)
    from src.config import MOD_CLOCK_RATES
    loop_rate_btn = CycleButton(MOD_CLOCK_RATES, initial_index=6)
    loop_rate_btn.setObjectName(f"mod{slot.slot_id}_env{output_idx}_loop_rate")
    loop_rate_btn.setFixedSize(30, btn_height)
    loop_rate_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
    loop_rate_btn.setStyleSheet(button_style('submenu'))
    loop_rate_btn.setToolTip("Loop rate (shift+click MODE to show/hide)")
    loop_rate_btn.text_alignment = Qt.AlignVCenter | Qt.AlignHCenter
    loop_rate_btn.text_padding_lr = 0
    loop_rate_btn.setVisible(False)
    loop_rate_btn.index_changed.connect(
        lambda idx, env_idx=output_idx: slot._on_env_loop_rate_changed(env_idx, idx)
    )
    row_widgets['loop_rate'] = loop_rate_btn

    # SYN/LOP toggle
    sync_btn = CycleButton(ARSEQ_SYNC_MODES, initial_index=0)
    sync_btn.setObjectName(f"mod{slot.slot_id}_env{output_idx}_sync")
    sync_btn.setFixedSize(30, btn_height)
    sync_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
    sync_btn.setStyleSheet(button_style('submenu'))
    sync_btn.setToolTip("SYN: master / LOP: loop (shift+click for rate)")
    sync_btn.text_alignment = Qt.AlignVCenter | Qt.AlignHCenter
    sync_btn.text_padding_lr = 1
    sync_btn.index_changed.connect(
        lambda idx, env_idx=output_idx: slot._on_env_sync_mode_changed(env_idx, idx)
    )

    if output_idx == 0:
        sync_container = QVBoxLayout()
        sync_container.setSpacing(2)
        sync_container.setContentsMargins(0, 0, 0, 0)
        sync_label = QLabel("MODE*")
        sync_label.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        sync_label.setAlignment(Qt.AlignCenter)
        sync_label.setStyleSheet(f"color: {COLORS['text']};")
        sync_label.setToolTip("Shift+click to show rate selector")
        sync_container.addWidget(sync_label)
        sync_container.addWidget(sync_btn)
        sync_container.addWidget(loop_rate_btn)
        row.addLayout(sync_container)
    else:
        row.addWidget(sync_btn)
        row.addWidget(loop_rate_btn)
    row_widgets['sync_mode'] = sync_btn

    # Shift+click on MODE shows rate selector (only in LOP mode)
    def toggle_rate_visibility(sync=sync_btn, rate=loop_rate_btn):
        if sync.index == 1:  # Only in LOP mode
            if rate.isVisible():
                rate.setVisible(False)
                sync.setVisible(True)
            else:
                rate.setVisible(True)
                sync.setVisible(False)

    sync_btn.shift_click_callback = toggle_rate_visibility
    loop_rate_btn.shift_click_callback = toggle_rate_visibility

    # Polarity N/I toggle
    pol_btn = CycleButton(MOD_POLARITY, initial_index=0)
    pol_btn.setObjectName(f"mod{slot.slot_id}_env{output_idx}_pol")
    pol_btn.setFixedSize(20, btn_height)
    pol_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
    pol_btn.setStyleSheet(button_style('submenu'))
    pol_btn.setToolTip("N/I")
    pol_btn.text_alignment = Qt.AlignVCenter | Qt.AlignHCenter
    pol_btn.text_padding_lr = 0
    pol_btn.value_changed.connect(
        lambda p, idx=output_idx, pols=MOD_POLARITY: slot._on_polarity_changed(idx, pols.index(p))
    )

    if output_idx == 0:
        pol_container = QVBoxLayout()
        pol_container.setSpacing(2)
        pol_container.setContentsMargins(0, 0, 0, 0)
        pol_label = QLabel("INV")
        pol_label.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        pol_label.setAlignment(Qt.AlignCenter)
        pol_label.setStyleSheet(f"color: {COLORS['text']};")
        pol_container.addWidget(pol_label)
        pol_container.addWidget(pol_btn)
        row.addLayout(pol_container)
    else:
        row.addWidget(pol_btn)
    row_widgets['polarity'] = pol_btn

    return row, row_widgets


def build_saucegrav_output_row(slot, output_idx, label):
    """Build a SauceOfGrav output row with TENS/MASS sliders and polarity."""
    mt = MODULATOR_THEME
    row = QHBoxLayout()
    row.setSpacing(4)
    row.setContentsMargins(0, 0, 0, 0)

    row_widgets = {}
    btn_height = 20

    # Output label (1-4)
    out_label = QLabel(label)
    out_label.setFont(QFont(MONO_FONT, FONT_SIZES['small'], QFont.Bold))
    out_label.setStyleSheet(f"color: {COLORS['text_bright']};")
    out_label.setFixedWidth(12)
    out_label.setToolTip(f"Output {label}")
    row.addWidget(out_label)
    row_widgets['label'] = out_label

    # TENS slider (horizontal) - with label on first row
    tension_slider = DragSlider()
    tension_slider.setObjectName(f"mod{slot.slot_id}_out{output_idx}_tension")
    tension_slider.setOrientation(Qt.Horizontal)
    tension_slider.setFixedHeight(btn_height)
    tension_slider.setMinimumWidth(30)
    # Stagger tension for varied behavior
    tension_defaults = [300, 450, 550, 700]  # low→high coupling
    tension_slider.setValue(tension_defaults[output_idx] if output_idx < 4 else 500)
    tension_slider.setToolTip("TENS: low=independent, high=coupled")
    tension_slider.valueChanged.connect(
        lambda val, idx=output_idx: slot._on_tension_changed(idx, val)
    )

    if output_idx == 0:
        tens_container = QVBoxLayout()
        tens_container.setSpacing(2)
        tens_container.setContentsMargins(0, 0, 0, 0)
        tens_label = QLabel("TENS")
        tens_label.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        tens_label.setAlignment(Qt.AlignCenter)
        tens_label.setStyleSheet(f"color: {COLORS['text']};")
        tens_container.addWidget(tens_label)
        tens_container.addWidget(tension_slider)
        row.addLayout(tens_container, 1)
    else:
        row.addWidget(tension_slider, 1)
    row_widgets['tension'] = tension_slider

    # MASS slider (horizontal) - with label on first row
    mass_slider = DragSlider()
    mass_slider.setObjectName(f"mod{slot.slot_id}_out{output_idx}_mass")
    mass_slider.setOrientation(Qt.Horizontal)
    mass_slider.setFixedHeight(btn_height)
    mass_slider.setMinimumWidth(30)
    # Stagger mass for varied character
    mass_defaults = [650, 550, 450, 350]  # slow→snappy
    mass_slider.setValue(mass_defaults[output_idx] if output_idx < 4 else 500)
    mass_slider.setToolTip("MASS: low=snappy, high=slow arcs")
    mass_slider.valueChanged.connect(
        lambda val, idx=output_idx: slot._on_mass_changed(idx, val)
    )

    if output_idx == 0:
        mass_container = QVBoxLayout()
        mass_container.setSpacing(2)
        mass_container.setContentsMargins(0, 0, 0, 0)
        mass_label = QLabel("MASS")
        mass_label.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        mass_label.setAlignment(Qt.AlignCenter)
        mass_label.setStyleSheet(f"color: {COLORS['text']};")
        mass_container.addWidget(mass_label)
        mass_container.addWidget(mass_slider)
        row.addLayout(mass_container, 1)
    else:
        row.addWidget(mass_slider, 1)
    row_widgets['mass'] = mass_slider

    # Polarity N/I toggle
    pol_btn = CycleButton(MOD_POLARITY, initial_index=0)
    pol_btn.setObjectName(f"mod{slot.slot_id}_out{output_idx}_pol")
    pol_btn.setFixedSize(20, btn_height)
    pol_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
    pol_btn.setStyleSheet(button_style('submenu'))
    pol_btn.setToolTip("N/I: normal or inverted")
    pol_btn.text_alignment = Qt.AlignVCenter | Qt.AlignHCenter
    pol_btn.text_padding_lr = 0
    pol_btn.value_changed.connect(
        lambda p, idx=output_idx, pols=MOD_POLARITY: slot._on_polarity_changed(idx, pols.index(p))
    )
    row.addWidget(pol_btn)
    row_widgets['polarity'] = pol_btn

    return row, row_widgets


def build_modulator_slot_ui(slot):
    """Build the complete modulator slot UI."""
    layout = QVBoxLayout(slot)
    layout.setContentsMargins(SIZES['margin_tight'], SIZES['margin_tight'],
                               SIZES['margin_tight'], SIZES['margin_tight'])
    layout.setSpacing(SIZES['spacing_normal'])
    
    # Header
    header = build_modulator_header(slot)
    layout.addLayout(header)
    
    # Separator
    sep = build_modulator_separator()
    layout.addWidget(sep)
    
    # Slider section (params)
    params = build_modulator_slider_section(slot)
    layout.addWidget(params)
    
    # Output section
    outputs = build_modulator_output_section(slot)
    layout.addWidget(outputs)
    
    # Scope
    scope = build_modulator_scope(slot)
    layout.addWidget(scope)
    
    layout.addStretch()
    
    # Base styling
    slot.setStyleSheet(f"""
        ModulatorSlot {{
            border: 2px solid {COLORS['border']};
            border-radius: 6px;
            background-color: {COLORS['background_light']};
        }}
    """)
    slot.setFixedWidth(156)
