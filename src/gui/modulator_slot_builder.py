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


def build_modulator_header(slot):
    """Build the header row with slot ID and generator selector."""
    mt = MODULATOR_THEME
    header = QHBoxLayout()
    header.setSpacing(mt['header_spacing'])
    
    # Slot number
    slot.id_label = QLabel(f"MOD {slot.slot_id}")
    slot.id_label.setObjectName(f"mod{slot.slot_id}_label")  # DEBUG
    slot.id_label.setFont(QFont(FONT_FAMILY, FONT_SIZES['small'], QFont.Bold))
    slot.id_label.setStyleSheet(f"color: {COLORS['text_bright']};")
    header.addWidget(slot.id_label)
    
    header.addStretch()
    
    # Generator selector button
    initial_idx = MOD_GENERATOR_CYCLE.index(slot.default_generator) if slot.default_generator in MOD_GENERATOR_CYCLE else 0
    slot.gen_button = CycleButton(MOD_GENERATOR_CYCLE, initial_index=initial_idx)
    slot.gen_button.setObjectName(f"mod{slot.slot_id}_type")  # DEBUG
    slot.gen_button.setFixedSize(mt['header_button_width'], mt['header_button_height'])
    # CRITICAL: allow shrink below sizeHint, prevents overflow
    slot.gen_button.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
    slot.gen_button.setMinimumWidth(0)
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
    slot.params_layout.setSpacing(mt['slider_row_spacing'])
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
    slot.scope.setObjectName(f"mod{slot.slot_id}_scope")  # DEBUG
    slot.scope.setFixedHeight(mt['scope_height'])  # FIXED: uses theme value
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
    is_mode_btn = key == 'mode' and steps_i in (2, 3)
    col_width = mt.get('mode_button_width', 48) if is_mode_btn else mt['slider_column_width']
    
    # Fixed-width column widget
    col = QWidget()
    col.setFixedWidth(col_width)
    col.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
    
    container = QVBoxLayout(col)
    container.setContentsMargins(0, 0, 0, 0)
    container.setSpacing(2)
    
    # Label - CRITICAL: fixed width prevents column expansion
    label = QLabel(param.get('label', key.upper()[:4]))
    label.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
    label.setAlignment(Qt.AlignCenter)
    label.setStyleSheet(f"color: {COLORS['text']};")
    label.setToolTip(param.get('tooltip', ''))
    label.setFixedHeight(mt['param_label_height'])
    label.setFixedWidth(col_width)
    label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    container.addWidget(label)
    
    # Use CycleButton for stepped params (mode: CLK/FREE for LFO, TOR/APA/INE for Sloth)
    if is_mode_btn:
        if steps_i == 2:
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
        btn.setObjectName(f"mod{slot.slot_id}_mode")  # DEBUG
        # Mode buttons need specific width to show text like "CLK", "FREE"
        mode_width = mt.get('mode_button_width', 48)
        mode_height = mt.get('mode_button_height', 22)
        btn.setFixedSize(mode_width, mode_height)  # FIXED: uses theme values
        btn.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        btn.setStyleSheet(button_style('submenu'))
        btn.setToolTip(tooltip)
        btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        # Center-align text
        btn.text_alignment = Qt.AlignVCenter | Qt.AlignHCenter
        btn.text_padding_lr = 2
        btn.index_changed.connect(
            lambda idx, k=key: slot._on_mode_changed(k, idx)
        )
        container.addWidget(btn)
        slot.param_sliders[key] = btn
    else:
        # Standard slider for continuous params
        slider = DragSlider()
        slider.setFixedWidth(mt.get('slider_width', 25))   # FIXED: uses theme value
        slider.setFixedHeight(mt.get('slider_height', 60))  # FIXED: uses theme value
        slider.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        default = param.get('default', 0.5)
        slider.setValue(int(default * 1000))
        
        slider.valueChanged.connect(
            lambda val, k=key, p=param: slot._on_param_changed(k, val, p)
        )
        container.addWidget(slider, alignment=Qt.AlignCenter)
        slot.param_sliders[key] = slider
    
    return col


def build_output_row(slot, output_idx, label, output_config):
    """Build an output row with controls."""
    mt = MODULATOR_THEME
    row = QHBoxLayout()
    row.setSpacing(4)
    
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
        wave_btn.setObjectName(f"mod{slot.slot_id}_wave{output_idx}")  # DEBUG
        wave_btn.setFixedSize(mt.get('wave_button_width', 40), btn_height)  # FIXED: theme values
        wave_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        wave_btn.setStyleSheet(button_style('submenu'))
        wave_btn.setToolTip("Waveform: Saw/Tri/Sqr/Sin/S&H")
        wave_btn.text_alignment = Qt.AlignVCenter | Qt.AlignHCenter
        wave_btn.text_padding_lr = 2
        wave_btn.value_changed.connect(
            lambda w, idx=output_idx, wforms=MOD_LFO_WAVEFORMS: slot._on_wave_changed(idx, wforms.index(w))
        )
        row.addWidget(wave_btn)
        row_widgets['wave'] = wave_btn
        
        # Only add per-output phase for old "waveform_phase" config (backward compat)
        if output_config == "waveform_phase":
            # Default phases: A=0° (idx 0), B=135° (idx 3), C=225° (idx 5)
            default_phase_indices = [0, 3, 5, 6]  # 4 outputs now
            phase_labels = [f"{p}°" for p in MOD_LFO_PHASES]
            phase_btn = CycleButton(phase_labels, initial_index=default_phase_indices[output_idx] if output_idx < len(default_phase_indices) else 0)
            phase_btn.setObjectName(f"mod{slot.slot_id}_phase{output_idx}")  # DEBUG
            phase_btn.setFixedSize(mt.get('phase_button_width', 38), btn_height)  # FIXED: theme values
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
    
    # Polarity button (all generators)
    # Default: BI for most, UNI for R output (Sloth gate)
    default_polarity = 0 if (output_config == "fixed" and output_idx == 3) else 1
    pol_btn = CycleButton(MOD_POLARITY, initial_index=default_polarity)
    pol_btn.setObjectName(f"mod{slot.slot_id}_pol{output_idx}")  # DEBUG
    pol_btn.setFixedSize(mt.get('pol_button_width', 28), btn_height)  # FIXED: theme values
    pol_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
    pol_btn.setStyleSheet(button_style('submenu'))
    pol_btn.setToolTip("Invert: NORM (original) / INV (flipped)")
    pol_btn.text_alignment = Qt.AlignVCenter | Qt.AlignHCenter
    pol_btn.text_padding_lr = 2
    pol_btn.value_changed.connect(
        lambda p, idx=output_idx, pols=MOD_POLARITY: slot._on_polarity_changed(idx, pols.index(p))
    )
    row.addWidget(pol_btn)
    row_widgets['polarity'] = pol_btn
    
    row.addStretch()
    
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
    slot.setMinimumWidth(140)
