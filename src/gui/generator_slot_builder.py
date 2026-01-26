"""
Generator Slot UI Builder
Handles layout construction for GeneratorSlot

Hierarchy:
- GeneratorHeader
- GeneratorContent
  - GeneratorSliderSection (custom + standard params)
  - GeneratorButtonStrip
"""

from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QWidget, QSizePolicy
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from .theme import (COLORS, button_style, MONO_FONT, FONT_FAMILY, FONT_SIZES,
                    mute_button_style, gate_indicator_style, midi_channel_style,
                    GENERATOR_THEME, slider_style)
from .widgets import DragSlider, CycleButton, MidiButton
from src.config import (
    FILTER_TYPES, CLOCK_RATES, CLOCK_DEFAULT_INDEX, SIZES,
    GENERATOR_PARAMS, MAX_CUSTOM_PARAMS, GENERATOR_CYCLE,
    ENV_SOURCES, TRANSPOSE_OPTIONS, TRANSPOSE_DEFAULT_INDEX
)

# MIDI channels - OFF plus 1-16
MIDI_CHANNELS = ["OFF"] + [str(i) for i in range(1, 17)]


def build_generator_header(slot):
    """Build the header row with slot ID and generator type selector."""
    gt = GENERATOR_THEME

    # Header widget - must expand to fill slot width
    header_widget = QWidget()
    header_widget.setObjectName(f"gen{slot.slot_id}_header")
    header_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    header = QHBoxLayout(header_widget)
    header.setSpacing(gt['header_spacing'])
    l = gt.get('header_inset_left', gt.get('header_inset_lr', 6))
    r = gt.get('header_inset_right', gt.get('header_inset_lr', 6))
    header.setContentsMargins(l, 0, r, 0)

    slot.id_label = QLabel(f"GEN {slot.slot_id}")
    slot.id_label.setObjectName(f"gen{slot.slot_id}_label")
    slot.id_label.setFont(QFont(FONT_FAMILY, FONT_SIZES['small']))
    slot.id_label.setStyleSheet(f"color: {COLORS['text']};")
    slot.id_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    slot.id_label.setContentsMargins(2, 0, 0, 0)
    header.addWidget(slot.id_label)

    # Push selector to the right edge
    header.addStretch(1)

    # Container to clip overflow
    type_offset = gt.get('header_type_offset_right', 0)
    btn_container = QFrame()
    btn_container.setObjectName(f"gen{slot.slot_id}_type_container")
    btn_container.setFixedWidth(gt.get('header_type_width', 75))
    btn_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    btn_container.setStyleSheet("background: transparent; border: none;")
    btn_layout = QHBoxLayout(btn_container)
    btn_layout.setContentsMargins(0, 0, -type_offset, 0)
    btn_layout.setSpacing(0)

    # Generator type selector
    initial_index = GENERATOR_CYCLE.index(slot.generator_type) if slot.generator_type in GENERATOR_CYCLE else 0
    slot.type_btn = CycleButton(GENERATOR_CYCLE, initial_index=initial_index)
    slot.type_btn.setObjectName(f"gen{slot.slot_id}_type")
    slot.type_btn.wrap = True
    slot.type_btn.skip_prefix = "────"
    slot.type_btn.sensitivity_key = 'generator'
    slot.type_btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['small'], QFont.Bold))
    w = gt.get('header_type_width', 75)
    slot.type_btn.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
    slot.type_btn.setMinimumWidth(0)
    slot.type_btn.setFixedWidth(w)
    slot.type_btn.setFixedHeight(gt.get('header_type_height', 22))
    slot.type_btn.setStyleSheet(f"""
        QPushButton {{
            color: {COLORS['enabled_text']};
            background: transparent;
            border: none;
            text-align: right;
            padding: 0px;
        }}
        QPushButton:hover {{
            color: {COLORS['enabled_text']};
        }}
    """)
    slot.type_btn.text_alignment = Qt.AlignVCenter | Qt.AlignLeft
    slot.type_btn.text_padding_lr = gt.get('header_selector_text_pad', 6)
    slot.type_btn.value_changed.connect(slot.on_generator_type_changed)
    btn_layout.addWidget(slot.type_btn)

    header.addWidget(btn_container)

    return header_widget


def build_param_slider(slot, param, custom_index=None):
    """Build a parameter slider with label - unified for standard and custom params.

    Args:
        slot: GeneratorSlot instance
        param: Param config dict (from GENERATOR_PARAMS or custom_params)
               For custom params, can be None initially (updated when generator loads)
        custom_index: If set (0-4), this is a custom param P1-P5

    Returns:
        (column_widget, label, slider)
    """
    gt = GENERATOR_THEME
    col_w = gt['slider_column_width']

    is_custom = custom_index is not None

    # Fixed-width column
    col = QWidget()
    col.setFixedWidth(col_w)
    col.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

    container = QVBoxLayout(col)
    container.setContentsMargins(0, 0, 0, 0)
    container.setSpacing(1)

    # Label
    if is_custom:
        label_text = f"P{custom_index + 1}"
        label_color = gt['param_label_color_dim']
    else:
        label_text = param['label']
        label_color = gt['param_label_color']

    font_weight = QFont.Bold if gt['param_label_bold'] else QFont.Normal
    lbl = QLabel(label_text)
    lbl.setFont(QFont(gt['param_label_font'], gt['param_label_size'], font_weight))
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setFixedHeight(gt['param_label_height'])
    lbl.setFixedWidth(col_w)
    lbl.setStyleSheet(f"color: {label_color};")
    container.addWidget(lbl)

    # Slider
    slider = DragSlider()
    slider.setFixedWidth(gt.get('slider_width', 25))
    slider.setFixedHeight(gt.get('slider_height', 60))

    # Set objectName to match unified bus target keys (for boid glow + MIDI mapping)
    if is_custom:
        slider.setObjectName(f"gen_{slot.slot_id}_custom{custom_index}")
    else:
        slider.setObjectName(f"gen_{slot.slot_id}_{param['key']}")

    if param:
        default = param.get('default', 0.5)
        slider.setValue(int(default * 1000))
        if 'tooltip' in param:
            slider.setToolTip(param['tooltip'])

    slider.setEnabled(False)  # Enabled when generator loads

    # Connect signal (convert 0-1000 to 0.0-1.0)
    if is_custom:
        slider.valueChanged.connect(
            lambda val, idx=custom_index: slot.on_custom_param_changed(idx, val / 1000.0)
        )
    else:
        slider.valueChanged.connect(
            lambda val, p=param: slot.on_param_changed(p['key'], val / 1000.0, p)
        )

    container.addWidget(slider, alignment=Qt.AlignHCenter)
    container.addStretch()

    return col, lbl, slider


def build_custom_params_row(slot):
    """Build the custom parameters row (P1-P5)."""
    gt = GENERATOR_THEME
    row = QHBoxLayout()
    row.setSpacing(gt['slider_gap'])

    slot.custom_sliders = []
    slot.custom_labels = []

    for i in range(MAX_CUSTOM_PARAMS):
        col, lbl, slider = build_param_slider(slot, None, custom_index=i)
        slot.custom_sliders.append(slider)
        slot.custom_labels.append(lbl)
        row.addWidget(col)

    return row


def build_standard_params_row(slot):
    """Build the standard parameters row (FRQ, CUT, RES, ATK, DEC)."""
    gt = GENERATOR_THEME
    row = QHBoxLayout()
    row.setSpacing(gt['slider_gap'])

    slot.sliders = {}
    slot.slider_labels = {}

    for param in GENERATOR_PARAMS:
        col, lbl, slider = build_param_slider(slot, param)
        slot.sliders[param['key']] = slider
        slot.slider_labels[param['key']] = lbl
        row.addWidget(col)

    return row


def build_generator_button_strip(slot):
    """Build the right-side buttons strip using theme config for order and styling."""
    gt = GENERATOR_THEME
    strip_config = gt['button_strip']
    button_order = gt['button_strip_order']

    strip = QWidget()
    strip.setFixedWidth(gt['button_strip_width'])
    layout = QVBoxLayout(strip)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(gt['button_strip_spacing'])

    # Build buttons in theme-defined order
    for btn_key in button_order:
        cfg = strip_config[btn_key]
        btn_width = cfg.get('width', 36)
        btn_height = cfg.get('height', 24)

        if btn_key == 'filter':
            slot.filter_btn = CycleButton(FILTER_TYPES, initial_index=0)
            slot.filter_btn.setObjectName(f"gen{slot.slot_id}_filter")
            btn = slot.filter_btn
            btn.setFixedSize(btn_width, btn_height)
            btn.setFont(QFont(cfg['font'], cfg['font_size'], QFont.Bold if cfg['font_bold'] else QFont.Normal))
            btn.setStyleSheet(button_style(cfg['style']))
            btn.wrap = True
            btn.value_changed.connect(slot.on_filter_changed)
            btn.setEnabled(False)

        elif btn_key == 'env':
            slot.env_btn = CycleButton(ENV_SOURCES, initial_index=0)
            slot.env_btn.setObjectName(f"gen{slot.slot_id}_env")
            btn = slot.env_btn
            btn.setFixedSize(btn_width, btn_height)
            btn.setFont(QFont(cfg['font'], cfg['font_size'], QFont.Bold if cfg['font_bold'] else QFont.Normal))
            btn.setStyleSheet(button_style(cfg['style']))
            btn.wrap = True
            btn.value_changed.connect(slot.on_env_source_changed)
            btn.setEnabled(False)

        elif btn_key == 'rate':
            slot.rate_btn = CycleButton(CLOCK_RATES, initial_index=CLOCK_DEFAULT_INDEX)
            slot.rate_btn.setObjectName(f"gen{slot.slot_id}_rate")
            btn = slot.rate_btn
            btn.setFixedSize(btn_width, btn_height)
            btn.setFont(QFont(cfg['font'], cfg['font_size'], QFont.Bold if cfg['font_bold'] else QFont.Normal))
            btn.setStyleSheet(button_style(cfg['style']))
            btn.wrap = True
            btn.value_changed.connect(slot.on_rate_changed)
            btn.setEnabled(False)

        elif btn_key == 'transpose':
            slot.transpose_btn = CycleButton(TRANSPOSE_OPTIONS, initial_index=TRANSPOSE_DEFAULT_INDEX)
            slot.transpose_btn.setObjectName(f"gen{slot.slot_id}_transpose")
            btn = slot.transpose_btn
            btn.setFixedSize(btn_width, btn_height)
            btn.setFont(QFont(cfg['font'], cfg['font_size'], QFont.Bold if cfg['font_bold'] else QFont.Normal))
            btn.setStyleSheet(button_style(cfg['style']))
            btn.wrap = True
            btn.value_changed.connect(slot.on_transpose_changed)
            btn.setEnabled(False)

        elif btn_key == 'midi':
            slot.midi_btn = CycleButton(MIDI_CHANNELS, initial_index=0)
            slot.midi_btn.setObjectName(f"gen{slot.slot_id}_midi")
            btn = slot.midi_btn
            btn.setFixedSize(btn_width, btn_height)
            btn.setFont(QFont(cfg['font'], cfg['font_size'], QFont.Bold if cfg['font_bold'] else QFont.Normal))
            btn.setStyleSheet(midi_channel_style(False))
            btn.wrap = True
            btn.value_changed.connect(slot.on_midi_channel_changed)

        elif btn_key == 'mute':
            slot.mute_btn = MidiButton("M")
            slot.mute_btn.setObjectName(f"gen{slot.slot_id}_mute")
            btn = slot.mute_btn
            btn.setFixedSize(btn_width, btn_height)
            btn.setFont(QFont(cfg['font'], cfg['font_size'], QFont.Bold if cfg['font_bold'] else QFont.Normal))
            btn.setStyleSheet(mute_button_style(False))
            btn.clicked.connect(slot.toggle_mute)

        elif btn_key == 'gate':
            slot.gate_led = QLabel()
            slot.gate_led.setObjectName(f"gen{slot.slot_id}_gate")
            btn = slot.gate_led
            btn.setFixedSize(btn_width, btn_height)
            btn.setStyleSheet(gate_indicator_style(False))
            btn.setAlignment(Qt.AlignCenter)

        btn.setToolTip(cfg['tooltip'])
        layout.addWidget(btn, alignment=Qt.AlignCenter)

        # Portamento knob  # ADD FROM HERE
    slot.portamento_knob = DragSlider()
    slot.portamento_knob.setObjectName(f"gen{slot.slot_id}_portamento")
    slot.portamento_knob.setFixedWidth(gt.get('slider_width', 25))
    slot.portamento_knob.setFixedHeight(gt.get('slider_height', 60))
    slot.portamento_knob.setValue(0)  # Default 0 (no glide)
    slot.portamento_knob.setToolTip("Portamento glide time (0=off, 1=full)")
    slot.portamento_knob.setEnabled(False)  # Enable when generator loads
    slot.portamento_knob.valueChanged.connect(
        lambda val: slot.on_portamento_changed(val / 1000.0)
    )
    layout.addWidget(slot.portamento_knob, alignment=Qt.AlignCenter)  # TO HERE

    layout.addStretch()

    return strip


def build_generator_slot_ui(slot):
    """Build the complete generator slot UI."""
    gt = GENERATOR_THEME

    # Constrain slot to not expand beyond allocated space
    slot.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

    layout = QVBoxLayout(slot)
    margin = gt['slot_margin']
    padding = gt['frame_padding']
    layout.setContentsMargins(
        margin[0] + padding[0],
        margin[1] + padding[1],
        margin[2] + padding[2],
        margin[3] + padding[3]
    )
    layout.setSpacing(gt.get('header_content_gap', 6))

    # Header
    header = build_generator_header(slot)
    layout.addWidget(header)

    # Content row (sliders left, buttons right)
    content_row = QHBoxLayout()
    content_row.setSpacing(gt.get('content_row_spacing', SIZES['spacing_normal']))

    # Slider section (left side)
    slider_section = QVBoxLayout()
    slider_section.setSpacing(gt.get('slider_section_spacing', 8))

    # Custom params row (P1-P5)
    custom_row = build_custom_params_row(slot)
    slider_section.addLayout(custom_row)

    # Standard params row (FRQ, CUT, RES, ATK, DEC)
    standard_row = build_standard_params_row(slot)
    slider_section.addLayout(standard_row)

    content_row.addLayout(slider_section)

    # Button strip (right side)
    button_strip = build_generator_button_strip(slot)
    content_row.addWidget(button_strip)

    layout.addLayout(content_row)

    # Base styling (applied after children created)
    slot.setStyleSheet(f"""
            GeneratorSlot {{
                border: 2px solid {COLORS['border']};
                border-radius: 6px;
                background-color: {COLORS['background']};
            }}
        """)

    # Re-apply slider styles after parent stylesheet (prevents cascade override)
    for slider in slot.sliders.values():
        slider.setStyleSheet(slider_style())
    for slider in slot.custom_sliders:
        slider.setStyleSheet(slider_style())