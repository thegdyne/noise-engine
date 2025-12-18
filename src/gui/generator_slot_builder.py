"""
Generator Slot UI Builder
Handles layout construction for GeneratorSlot
"""

from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QWidget, QSizePolicy
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from .theme import (COLORS, button_style, MONO_FONT, FONT_FAMILY, FONT_SIZES,
                    mute_button_style, gate_indicator_style, midi_channel_style,
                    GENERATOR_THEME)
from .widgets import MiniSlider, CycleButton
from src.config import (
    FILTER_TYPES, CLOCK_RATES, CLOCK_DEFAULT_INDEX, SIZES,
    GENERATOR_PARAMS, MAX_CUSTOM_PARAMS, GENERATOR_CYCLE,
    ENV_SOURCES
)

# MIDI channels - OFF plus 1-16
MIDI_CHANNELS = ["OFF"] + [str(i) for i in range(1, 17)]


def build_generator_header(slot):
    """Build the header row with slot ID and generator type selector."""
    gt = GENERATOR_THEME
    
    # Header widget - must expand to fill slot width
    header_widget = QWidget()
    header_widget.setObjectName(f"gen{slot.slot_id}_header")  # DEBUG
    header_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    header = QHBoxLayout(header_widget)
    header.setSpacing(gt['header_spacing'])
    l = gt.get('header_inset_left', gt.get('header_inset_lr', 6))
    r = gt.get('header_inset_right', gt.get('header_inset_lr', 6))
    header.setContentsMargins(l, 0, r, 0)
    
    slot.id_label = QLabel(f"GEN {slot.slot_id}")
    slot.id_label.setObjectName(f"gen{slot.slot_id}_label")  # DEBUG
    slot.id_label.setFont(QFont(FONT_FAMILY, FONT_SIZES['small']))
    slot.id_label.setStyleSheet(f"color: {COLORS['text']};")
    slot.id_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    slot.id_label.setContentsMargins(2, 0, 0, 0)  # small left pad to match right pad
    header.addWidget(slot.id_label)
    
    # CRITICAL: push selector to the right edge
    header.addStretch(1)
    
    # Container to clip overflow
    type_offset = gt.get('header_type_offset_right', 0)
    btn_container = QFrame()
    btn_container.setObjectName(f"gen{slot.slot_id}_type_container")  # DEBUG
    btn_container.setFixedWidth(gt.get('header_type_width', 75))
    btn_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    btn_container.setStyleSheet("background: transparent; border: none;")
    btn_layout = QHBoxLayout(btn_container)
    # Negative right margin shifts content past container edge
    btn_layout.setContentsMargins(0, 0, -type_offset, 0)
    btn_layout.setSpacing(0)
    
    # Generator type selector
    initial_index = GENERATOR_CYCLE.index(slot.generator_type) if slot.generator_type in GENERATOR_CYCLE else 0
    slot.type_btn = CycleButton(GENERATOR_CYCLE, initial_index=initial_index)
    slot.type_btn.setObjectName(f"gen{slot.slot_id}_type")  # DEBUG: shows in overlay
    slot.type_btn.wrap = True
    slot.type_btn.skip_prefix = "────"  # Skip pack separator entries
    slot.type_btn.sensitivity_key = 'generator'
    slot.type_btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['small'], QFont.Bold))
    # CRITICAL: allow shrink below sizeHint, prevents spill/overflow
    w = gt.get('header_type_width', 75)
    slot.type_btn.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
    slot.type_btn.setMinimumWidth(0)
    slot.type_btn.setFixedWidth(w)   # lock it to container width
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
    # Align text left inside the selector box (sits over button strip)
    slot.type_btn.text_alignment = Qt.AlignVCenter | Qt.AlignLeft
    slot.type_btn.text_padding_lr = gt.get('header_selector_text_pad', 6)
    slot.type_btn.value_changed.connect(slot.on_generator_type_changed)
    btn_layout.addWidget(slot.type_btn)
    
    header.addWidget(btn_container)
    
    return header_widget


def build_param_column(label_text, slider, label_style='dim'):
    """
    Build a single parameter column with label above slider.
    Unified layout for both custom (P1-P5) and standard (FRQ, CUT, etc.) params.
    
    Args:
        label_text: Text for the label
        slider: MiniSlider instance
        label_style: 'dim' for inactive/custom params, 'normal' for standard params
    
    Returns:
        (QWidget, QLabel) - the column widget and label for later updates
    """
    gt = GENERATOR_THEME
    col_w = gt['slider_column_width']
    
    widget = QWidget()
    widget.setFixedWidth(col_w)
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(1)
    
    # Label styling from generator theme
    font_weight = QFont.Bold if gt['param_label_bold'] else QFont.Normal
    
    lbl = QLabel(label_text)
    lbl.setFont(QFont(gt['param_label_font'], gt['param_label_size'], font_weight))
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setFixedHeight(gt['param_label_height'])
    lbl.setFixedWidth(col_w)
    
    if label_style == 'dim':
        lbl.setStyleSheet(f"color: {gt['param_label_color_dim']};")
    else:
        lbl.setStyleSheet(f"color: {gt['param_label_color']};")
    
    layout.addWidget(lbl)
    
    # Slider fills remaining space
    layout.addWidget(slider, stretch=1, alignment=Qt.AlignCenter)
    
    return widget, lbl


def build_custom_params_row(slot):
    """Build the custom parameters row (P1-P5)."""
    gt = GENERATOR_THEME
    
    custom_row = QHBoxLayout()
    custom_row.setSpacing(gt['slider_gap'])
    
    slot.custom_sliders = []
    slot.custom_labels = []
    
    for i in range(MAX_CUSTOM_PARAMS):
        slider = MiniSlider()
        slider.setFixedWidth(gt['slider_column_width'])
        slider.setMinimumHeight(gt.get('slider_min_height', 50))
        slider.setEnabled(False)
        slider.normalizedValueChanged.connect(
            lambda norm, idx=i: slot.on_custom_param_changed(idx, norm)
        )
        slot.custom_sliders.append(slider)
        
        widget, lbl = build_param_column(f"P{i+1}", slider, label_style='dim')
        slot.custom_labels.append(lbl)
        custom_row.addWidget(widget)
    
    return custom_row


def build_standard_params_row(slot):
    """Build the standard parameters row (FRQ, CUT, RES, ATK, DEC)."""
    gt = GENERATOR_THEME
    
    params_layout = QHBoxLayout()
    params_layout.setSpacing(gt['slider_gap'])
    
    slot.sliders = {}
    slot.slider_labels = {}
    
    for param in GENERATOR_PARAMS:
        slider = MiniSlider(param_config=param)
        slider.setFixedWidth(gt['slider_column_width'])
        slider.setMinimumHeight(gt.get('slider_min_height', 50))
        slider.setToolTip(param['tooltip'])
        slider.normalizedValueChanged.connect(
            lambda norm, p=param: slot.on_param_changed(p['key'], norm, p)
        )
        slider.setEnabled(False)
        
        widget, lbl = build_param_column(param['label'], slider, label_style='normal')
        
        slot.sliders[param['key']] = slider
        slot.slider_labels[param['key']] = lbl
        params_layout.addWidget(widget)
    
    return params_layout


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
            slot.filter_btn.setObjectName(f"gen{slot.slot_id}_filter")  # DEBUG
            btn = slot.filter_btn
            btn.setFixedSize(btn_width, btn_height)
            btn.setFont(QFont(cfg['font'], cfg['font_size'], QFont.Bold if cfg['font_bold'] else QFont.Normal))
            btn.setStyleSheet(button_style(cfg['style']))
            btn.wrap = True
            btn.value_changed.connect(slot.on_filter_changed)
            btn.setEnabled(False)
            
        elif btn_key == 'env':
            slot.env_btn = CycleButton(ENV_SOURCES, initial_index=0)
            slot.env_btn.setObjectName(f"gen{slot.slot_id}_env")  # DEBUG
            btn = slot.env_btn
            btn.setFixedSize(btn_width, btn_height)
            btn.setFont(QFont(cfg['font'], cfg['font_size'], QFont.Bold if cfg['font_bold'] else QFont.Normal))
            btn.setStyleSheet(button_style(cfg['style']))
            btn.wrap = True
            btn.value_changed.connect(slot.on_env_source_changed)
            btn.setEnabled(False)
            
        elif btn_key == 'rate':
            slot.rate_btn = CycleButton(CLOCK_RATES, initial_index=CLOCK_DEFAULT_INDEX)
            slot.rate_btn.setObjectName(f"gen{slot.slot_id}_rate")  # DEBUG
            btn = slot.rate_btn
            btn.setFixedSize(btn_width, btn_height)
            btn.setFont(QFont(cfg['font'], cfg['font_size'], QFont.Bold if cfg['font_bold'] else QFont.Normal))
            btn.setStyleSheet(button_style(cfg['style']))
            btn.wrap = False
            btn.value_changed.connect(slot.on_rate_changed)
            btn.setEnabled(False)
            
        elif btn_key == 'midi':
            slot.midi_btn = CycleButton(MIDI_CHANNELS, initial_index=0)
            slot.midi_btn.setObjectName(f"gen{slot.slot_id}_midi")  # DEBUG
            btn = slot.midi_btn
            btn.setFixedSize(btn_width, btn_height)
            btn.setFont(QFont(cfg['font'], cfg['font_size'], QFont.Bold if cfg['font_bold'] else QFont.Normal))
            btn.setStyleSheet(midi_channel_style(False))
            btn.wrap = True
            btn.value_changed.connect(slot.on_midi_channel_changed)
            
        elif btn_key == 'mute':
            slot.mute_btn = QPushButton("M")
            slot.mute_btn.setObjectName(f"gen{slot.slot_id}_mute")  # DEBUG
            btn = slot.mute_btn
            btn.setFixedSize(btn_width, btn_height)
            btn.setFont(QFont(cfg['font'], cfg['font_size'], QFont.Bold if cfg['font_bold'] else QFont.Normal))
            btn.setStyleSheet(mute_button_style(False))
            btn.clicked.connect(slot.toggle_mute)
            
        elif btn_key == 'gate':
            slot.gate_led = QLabel()
            slot.gate_led.setObjectName(f"gen{slot.slot_id}_gate")  # DEBUG
            btn = slot.gate_led
            btn.setFixedSize(btn_width, btn_height)
            btn.setStyleSheet(gate_indicator_style(False))
            btn.setAlignment(Qt.AlignCenter)
        
        btn.setToolTip(cfg['tooltip'])
        layout.addWidget(btn, alignment=Qt.AlignCenter)
    
    layout.addStretch()
    
    return strip


def build_generator_slot_ui(slot):
    """Build the complete generator slot UI."""
    gt = GENERATOR_THEME
    
    # Constrain slot to not expand beyond allocated space
    from PyQt5.QtWidgets import QSizePolicy
    slot.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
    
    layout = QVBoxLayout(slot)
    margin = gt['slot_margin']
    layout.setContentsMargins(margin[0], margin[1], margin[2], margin[3])
    # Header now lives INSIDE the frame, so slot spacing can be small
    layout.setSpacing(0)
    
    # GeneratorFrame (contains header + sliders + buttons strip)
    generator_frame = QFrame()
    generator_frame.setObjectName("generatorFrame")
    generator_frame.setStyleSheet(f"""
        QFrame#generatorFrame {{
            background-color: {gt['frame_background']};
            border: {gt['frame_border_width']}px solid {gt['frame_border']};
            border-radius: {gt['frame_border_radius']}px;
        }}
    """)
    
    # Frame layout is VERTICAL: header on top, content row below
    padding = gt['frame_padding']
    frame_v = QVBoxLayout(generator_frame)
    frame_v.setContentsMargins(padding[0], padding[1], padding[2], padding[3])
    frame_v.setSpacing(gt.get('header_content_gap', 6))
    
    # Header inside frame
    generator_header = build_generator_header(slot)
    frame_v.addWidget(generator_header)
    
    # Content row (sliders left, buttons right)
    content_row = QHBoxLayout()
    content_row.setSpacing(gt.get('content_row_spacing', SIZES['spacing_normal']))
    
    # GeneratorSliderSection (left side)
    generator_slider_section = QVBoxLayout()
    generator_slider_section.setSpacing(gt.get('slider_section_spacing', 8))
    
    # Custom params row
    custom_row = build_custom_params_row(slot)
    generator_slider_section.addLayout(custom_row)
    
    # Standard params row
    params_row = build_standard_params_row(slot)
    generator_slider_section.addLayout(params_row)
    
    content_row.addLayout(generator_slider_section)
    
    # GeneratorButtonStrip (right side, inside frame)
    generator_button_strip = build_generator_button_strip(slot)
    content_row.addWidget(generator_button_strip)
    
    frame_v.addLayout(content_row)
    
    # Frame should not expand horizontally
    generator_frame.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
    
    layout.addWidget(generator_frame)
