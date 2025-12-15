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


def build_header(slot):
    """Build the header row with slot ID and generator type selector."""
    header = QHBoxLayout()
    
    slot.id_label = QLabel(f"GEN {slot.slot_id}")
    slot.id_label.setFont(QFont(FONT_FAMILY, FONT_SIZES['small']))
    slot.id_label.setStyleSheet(f"color: {COLORS['text']};")
    header.addWidget(slot.id_label)
    
    header.addStretch()
    
    # Generator type selector - drag or click to change
    initial_index = GENERATOR_CYCLE.index(slot.generator_type) if slot.generator_type in GENERATOR_CYCLE else 0
    slot.type_btn = CycleButton(GENERATOR_CYCLE, initial_index=initial_index)
    slot.type_btn.wrap = True
    slot.type_btn.sensitivity_key = 'generator'
    slot.type_btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['slot_title'], QFont.Bold))
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
    
    # Spacer to match buttons column
    custom_spacer = QWidget()
    custom_spacer.setFixedWidth(SIZES['buttons_column_width'] + 5)
    custom_row.addWidget(custom_spacer)
    
    return custom_row


def build_standard_params_row(slot):
    """Build the standard parameters row (FRQ, CUT, RES, ATK, DEC) + buttons."""
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
    
    params_layout.addSpacing(5)
    
    # Add buttons column
    buttons_widget = build_buttons_column(slot)
    params_layout.addWidget(buttons_widget)
    
    return params_layout


def build_buttons_column(slot):
    """Build the buttons column (filter, ENV, rate, MIDI, mute/gate)."""
    buttons_widget = QWidget()
    buttons_widget.setFixedWidth(SIZES['buttons_column_width'])
    buttons_layout = QVBoxLayout(buttons_widget)
    buttons_layout.setContentsMargins(0, 0, 0, 0)
    buttons_layout.setSpacing(3)
    
    # Filter type - CycleButton
    slot.filter_btn = CycleButton(FILTER_TYPES, initial_index=0)
    slot.filter_btn.setFixedSize(*SIZES['button_medium'])
    slot.filter_btn.setFont(QFont(MONO_FONT, FONT_SIZES['small'], QFont.Bold))
    slot.filter_btn.setStyleSheet(button_style('enabled'))
    slot.filter_btn.wrap = True
    slot.filter_btn.value_changed.connect(slot.on_filter_changed)
    slot.filter_btn.setEnabled(False)
    slot.filter_btn.setToolTip("Filter Type: LP / HP / BP")
    buttons_layout.addWidget(slot.filter_btn)
    
    # ENV source - CycleButton (OFF/CLK/MIDI)
    slot.env_btn = CycleButton(ENV_SOURCES, initial_index=0)
    slot.env_btn.setFixedSize(*SIZES['button_medium'])
    slot.env_btn.setFont(QFont(MONO_FONT, FONT_SIZES['tiny'], QFont.Bold))
    slot.env_btn.setStyleSheet(button_style('disabled'))
    slot.env_btn.wrap = True
    slot.env_btn.value_changed.connect(slot.on_env_source_changed)
    slot.env_btn.setEnabled(False)
    slot.env_btn.setToolTip("Envelope source: OFF (drone), CLK (clock), MIDI")
    buttons_layout.addWidget(slot.env_btn)
    
    # CLK rate - CycleButton
    slot.rate_btn = CycleButton(CLOCK_RATES, initial_index=CLOCK_DEFAULT_INDEX)
    slot.rate_btn.setFixedSize(*SIZES['button_medium'])
    slot.rate_btn.setFont(QFont(MONO_FONT, FONT_SIZES['tiny']))
    slot.rate_btn.setStyleSheet(button_style('inactive'))
    slot.rate_btn.wrap = False
    slot.rate_btn.value_changed.connect(slot.on_rate_changed)
    slot.rate_btn.setEnabled(False)
    slot.rate_btn.setToolTip("Clock rate\n↑ faster: x8, x4, x2\n↓ slower: /2, /4, /8, /16")
    buttons_layout.addWidget(slot.rate_btn)
    
    # Separator/spacer
    buttons_layout.addSpacing(6)
    
    # MIDI channel selector
    slot.midi_btn = CycleButton(MIDI_CHANNELS, initial_index=0)
    slot.midi_btn.setFixedSize(*SIZES['button_medium'])
    slot.midi_btn.setFont(QFont(MONO_FONT, FONT_SIZES['tiny'], QFont.Bold))
    slot.midi_btn.setStyleSheet(midi_channel_style(False))
    slot.midi_btn.wrap = True
    slot.midi_btn.value_changed.connect(slot.on_midi_channel_changed)
    slot.midi_btn.setToolTip("MIDI Input Channel (OFF or 1-16)")
    buttons_layout.addWidget(slot.midi_btn)
    
    # Mute/Gate row
    mute_gate_row = QHBoxLayout()
    mute_gate_row.setSpacing(2)
    mute_gate_row.setContentsMargins(0, 0, 0, 0)
    
    slot.mute_btn = QPushButton("M")
    slot.mute_btn.setFixedSize(18, 18)
    slot.mute_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro'], QFont.Bold))
    slot.mute_btn.setStyleSheet(mute_button_style(False))
    slot.mute_btn.clicked.connect(slot.toggle_mute)
    slot.mute_btn.setToolTip("Mute Generator")
    mute_gate_row.addWidget(slot.mute_btn)
    
    slot.gate_led = QLabel()
    slot.gate_led.setFixedSize(18, 18)
    slot.gate_led.setStyleSheet(gate_indicator_style(False))
    slot.gate_led.setToolTip("Gate Activity")
    mute_gate_row.addWidget(slot.gate_led)
    
    buttons_layout.addLayout(mute_gate_row)
    buttons_layout.addStretch()
    
    return buttons_widget

def build_slot_ui(slot):
    """Build the complete generator slot UI."""
    layout = QVBoxLayout(slot)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(5)
    
    # Header
    header = build_header(slot)
    layout.addLayout(header)
    
    # Params frame
    params_frame = QFrame()
    params_frame.setStyleSheet(f"background-color: {COLORS['background']}; border-radius: 4px;")
    params_frame.setObjectName("paramsFrame")
    params_outer = QVBoxLayout(params_frame)
    params_outer.setContentsMargins(8, 8, 8, 8)
    params_outer.setSpacing(8)
    
    # Custom params row
    custom_row = build_custom_params_row(slot)
    params_outer.addLayout(custom_row)
    
    # Standard params row
    params_row = build_standard_params_row(slot)
    params_outer.addLayout(params_row)
    
    layout.addWidget(params_frame, stretch=1)  # Let params frame grow
