"""
Generator Slot UI Builder
Handles layout construction for GeneratorSlot
"""

from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QWidget
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
    header = QHBoxLayout()
    header.setSpacing(gt['header_spacing'])
    
    slot.id_label = QLabel(f"GEN {slot.slot_id}")
    slot.id_label.setFont(QFont(FONT_FAMILY, FONT_SIZES['small']))
    slot.id_label.setStyleSheet(f"color: {COLORS['text']};")
    header.addWidget(slot.id_label)
    
    header.addStretch()
    
    # Generator type selector - drag or click to change
    # Fixed width prevents scroll dead zone when name length changes
    initial_index = GENERATOR_CYCLE.index(slot.generator_type) if slot.generator_type in GENERATOR_CYCLE else 0
    slot.type_btn = CycleButton(GENERATOR_CYCLE, initial_index=initial_index)
    slot.type_btn.wrap = True
    slot.type_btn.sensitivity_key = 'generator'
    slot.type_btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['slot_title'], QFont.Bold))
    slot.type_btn.setFixedWidth(90)  # Fits longest name, consistent scroll target
    slot.type_btn.setStyleSheet(f"""
        QPushButton {{
            color: {COLORS['text']};
            background: transparent;
            border: none;
            text-align: right;
            padding: 2px 4px;
        }}
        QPushButton:hover {{
            color: {COLORS['enabled_text']};
        }}
    """)
    slot.type_btn.value_changed.connect(slot.on_generator_type_changed)
    header.addWidget(slot.type_btn)
    
    return header


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
    widget = QWidget()
    widget.setFixedWidth(35)  # Constrain column width
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)
    
    # Label styling from generator theme
    gt = GENERATOR_THEME
    font_weight = QFont.Bold if gt['param_label_bold'] else QFont.Normal
    
    lbl = QLabel(label_text)
    lbl.setFont(QFont(gt['param_label_font'], gt['param_label_size'], font_weight))
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setFixedHeight(gt['param_label_height'])
    
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
    custom_row = QHBoxLayout()
    custom_row.setSpacing(5)
    
    slot.custom_sliders = []
    slot.custom_labels = []
    
    for i in range(MAX_CUSTOM_PARAMS):
        slider = MiniSlider()
        slider.setMinimumHeight(50)  # Min height, can grow with window
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
    params_layout = QHBoxLayout()
    params_layout.setSpacing(5)
    
    slot.sliders = {}
    slot.slider_labels = {}
    
    for param in GENERATOR_PARAMS:
        slider = MiniSlider(param_config=param)
        slider.setMinimumHeight(50)  # Min height, can grow with window
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
            btn = slot.filter_btn
            btn.setFixedSize(btn_width, btn_height)
            btn.setFont(QFont(cfg['font'], cfg['font_size'], QFont.Bold if cfg['font_bold'] else QFont.Normal))
            btn.setStyleSheet(button_style(cfg['style']))
            btn.wrap = True
            btn.value_changed.connect(slot.on_filter_changed)
            btn.setEnabled(False)
            
        elif btn_key == 'env':
            slot.env_btn = CycleButton(ENV_SOURCES, initial_index=0)
            btn = slot.env_btn
            btn.setFixedSize(btn_width, btn_height)
            btn.setFont(QFont(cfg['font'], cfg['font_size'], QFont.Bold if cfg['font_bold'] else QFont.Normal))
            btn.setStyleSheet(button_style(cfg['style']))
            btn.wrap = True
            btn.value_changed.connect(slot.on_env_source_changed)
            btn.setEnabled(False)
            
        elif btn_key == 'rate':
            slot.rate_btn = CycleButton(CLOCK_RATES, initial_index=CLOCK_DEFAULT_INDEX)
            btn = slot.rate_btn
            btn.setFixedSize(btn_width, btn_height)
            btn.setFont(QFont(cfg['font'], cfg['font_size'], QFont.Bold if cfg['font_bold'] else QFont.Normal))
            btn.setStyleSheet(button_style(cfg['style']))
            btn.wrap = False
            btn.value_changed.connect(slot.on_rate_changed)
            btn.setEnabled(False)
            
        elif btn_key == 'midi':
            slot.midi_btn = CycleButton(MIDI_CHANNELS, initial_index=0)
            btn = slot.midi_btn
            btn.setFixedSize(btn_width, btn_height)
            btn.setFont(QFont(cfg['font'], cfg['font_size'], QFont.Bold if cfg['font_bold'] else QFont.Normal))
            btn.setStyleSheet(midi_channel_style(False))
            btn.wrap = True
            btn.value_changed.connect(slot.on_midi_channel_changed)
            
        elif btn_key == 'mute':
            slot.mute_btn = QPushButton("M")
            btn = slot.mute_btn
            btn.setFixedSize(btn_width, btn_height)
            btn.setFont(QFont(cfg['font'], cfg['font_size'], QFont.Bold if cfg['font_bold'] else QFont.Normal))
            btn.setStyleSheet(mute_button_style(False))
            btn.clicked.connect(slot.toggle_mute)
            
        elif btn_key == 'gate':
            slot.gate_led = QLabel()
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
    
    layout = QVBoxLayout(slot)
    margin = gt['slot_margin']
    layout.setContentsMargins(margin[0], margin[1], margin[2], margin[3])
    layout.setSpacing(gt['header_spacing'])
    
    # GeneratorHeader
    generator_header = build_generator_header(slot)
    layout.addLayout(generator_header)
    
    # GeneratorFrame (contains sliders + buttons strip)
    generator_frame = QFrame()
    generator_frame.setObjectName("generatorFrame")
    generator_frame.setStyleSheet(f"""
        QFrame#generatorFrame {{
            background-color: {gt['frame_background']};
            border: {gt['frame_border_width']}px solid {gt['frame_border']};
            border-radius: {gt['frame_border_radius']}px;
        }}
    """)
    
    # Horizontal layout: sliders on left, buttons on right
    frame_layout = QHBoxLayout(generator_frame)
    padding = gt['frame_padding']
    frame_layout.setContentsMargins(padding[0], padding[1], padding[2], padding[3])
    frame_layout.setSpacing(SIZES['spacing_normal'])
    
    # GeneratorSliderSection (left side)
    generator_slider_section = QVBoxLayout()
    generator_slider_section.setSpacing(8)
    
    # Custom params row
    custom_row = build_custom_params_row(slot)
    generator_slider_section.addLayout(custom_row)
    
    # Standard params row
    params_row = build_standard_params_row(slot)
    generator_slider_section.addLayout(params_row)
    
    frame_layout.addLayout(generator_slider_section, stretch=1)
    
    # GeneratorButtonStrip (right side, inside frame)
    generator_button_strip = build_generator_button_strip(slot)
    frame_layout.addWidget(generator_button_strip)
    
    layout.addWidget(generator_frame, stretch=1)
