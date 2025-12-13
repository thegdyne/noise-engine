"""
Generator Slot Component
Individual generator with base parameters
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

from .theme import (COLORS, button_style, MONO_FONT, FONT_FAMILY, FONT_SIZES,
                    mute_button_style, gate_indicator_style, midi_channel_style)
from .widgets import MiniSlider, CycleButton
from src.config import (
    FILTER_TYPES, CLOCK_RATES, CLOCK_DEFAULT_INDEX, SIZES,
    GENERATOR_PARAMS, MAX_CUSTOM_PARAMS, GENERATOR_CYCLE, map_value, 
    get_generator_custom_params, get_generator_pitch_target,
    get_generator_midi_retrig, get_generator_retrig_param_index,
    ENV_SOURCES, ENV_SOURCE_INDEX
)
from src.utils.logger import logger

# MIDI channels - OFF plus 1-16
MIDI_CHANNELS = ["OFF"] + [str(i) for i in range(1, 17)]


class GeneratorSlot(QWidget):
    """A single generator slot with base parameters."""
    
    clicked = pyqtSignal(int)  # Legacy - kept for compatibility
    generator_changed = pyqtSignal(int, str)  # slot_id, generator_type
    parameter_changed = pyqtSignal(int, str, float)  # slot_id, param_key, real_value
    custom_parameter_changed = pyqtSignal(int, int, float)  # slot_id, param_index, real_value
    filter_type_changed = pyqtSignal(int, str)
    clock_enabled_changed = pyqtSignal(int, bool)  # Legacy - kept for compatibility
    env_source_changed = pyqtSignal(int, int)  # slot_id, source (0=OFF, 1=CLK, 2=MIDI)
    clock_rate_changed = pyqtSignal(int, str)
    mute_changed = pyqtSignal(int, bool)  # slot_id, muted
    midi_channel_changed = pyqtSignal(int, int)  # slot_id, channel (0=OFF, 1-16)
    
    def __init__(self, slot_id, generator_type="Empty", parent=None):
        super().__init__(parent)
        self.slot_id = slot_id
        self.generator_type = generator_type
        self.active = False
        self.clock_enabled = False  # Legacy
        self.env_source = 0  # 0=OFF, 1=CLK, 2=MIDI
        self.muted = False
        self.midi_channel = 0  # 0 = OFF, 1-16 = channels
        
        # Gate indicator flash timer
        self.gate_timer = QTimer()
        self.gate_timer.timeout.connect(self._gate_off)
        self.gate_timer.setSingleShot(True)
        
        self.setMinimumSize(200, 220)
        self.setup_ui()
        self.update_style()
        
    def setup_ui(self):
        """Create slot interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(5)
        
        header = QHBoxLayout()
        
        self.id_label = QLabel(f"GEN {self.slot_id}")
        self.id_label.setFont(QFont(FONT_FAMILY, FONT_SIZES['small']))
        self.id_label.setStyleSheet(f"color: {COLORS['text']};")
        header.addWidget(self.id_label)
        
        header.addStretch()
        
        # Generator type selector - drag or click to change
        initial_index = GENERATOR_CYCLE.index(self.generator_type) if self.generator_type in GENERATOR_CYCLE else 0
        self.type_btn = CycleButton(GENERATOR_CYCLE, initial_index=initial_index)
        self.type_btn.wrap = True  # Wrap around list both directions
        self.type_btn.sensitivity_key = 'generator'  # Faster drag for long list
        self.type_btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['slot_title'], QFont.Bold))
        self.type_btn.setStyleSheet(f"""
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
        self.type_btn.value_changed.connect(self.on_generator_type_changed)
        header.addWidget(self.type_btn)
        
        layout.addLayout(header)
        
        params_frame = QFrame()
        params_frame.setStyleSheet(f"background-color: {COLORS['background']}; border-radius: 4px;")
        params_frame.setObjectName("paramsFrame")
        params_outer = QVBoxLayout(params_frame)
        params_outer.setContentsMargins(8, 8, 8, 8)
        params_outer.setSpacing(8)
        
        # === CUSTOM PARAMS ROW (per-generator) ===
        custom_row = QHBoxLayout()
        custom_row.setSpacing(5)
        
        self.custom_sliders = []
        self.custom_labels = []
        
        for i in range(MAX_CUSTOM_PARAMS):
            param_widget = QWidget()
            param_layout = QVBoxLayout(param_widget)
            param_layout.setContentsMargins(0, 0, 0, 0)
            param_layout.setSpacing(2)
            
            lbl = QLabel(f"P{i+1}")
            lbl.setFont(QFont(MONO_FONT, FONT_SIZES['tiny'], QFont.Bold))
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"color: {COLORS['text_dim']};")
            param_layout.addWidget(lbl)
            self.custom_labels.append(lbl)
            
            slider = MiniSlider()
            slider.setFixedHeight(60)  # Fixed height for consistency
            slider.setEnabled(False)
            slider.normalizedValueChanged.connect(
                lambda norm, idx=i: self.on_custom_param_changed(idx, norm)
            )
            param_layout.addWidget(slider, alignment=Qt.AlignCenter)
            self.custom_sliders.append(slider)
            
            custom_row.addWidget(param_widget)
        
        # Spacer to match buttons column
        custom_spacer = QWidget()
        custom_spacer.setFixedWidth(SIZES['buttons_column_width'] + 5)
        custom_row.addWidget(custom_spacer)
        
        params_outer.addLayout(custom_row)
        
        # === STANDARD PARAMS ROW ===
        params_layout = QHBoxLayout()
        params_layout.setSpacing(5)
        
        # Build sliders from config
        self.sliders = {}
        self.slider_labels = {}
        
        for param in GENERATOR_PARAMS:
            param_widget = QWidget()
            param_layout = QVBoxLayout(param_widget)
            param_layout.setContentsMargins(0, 0, 0, 0)
            param_layout.setSpacing(0)
            
            # Push content to bottom so label stays directly above slider
            param_layout.addStretch()
            
            lbl = QLabel(param['label'])
            lbl.setFont(QFont(MONO_FONT, FONT_SIZES['tiny'], QFont.Bold))
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"color: {COLORS['text']};")
            lbl.setFixedHeight(14)  # Fixed label height
            param_layout.addWidget(lbl, alignment=Qt.AlignHCenter)
            
            slider = MiniSlider(param_config=param)
            slider.setFixedHeight(60)  # Fixed height for consistency
            slider.setToolTip(param['tooltip'])
            slider.normalizedValueChanged.connect(
                lambda norm, p=param: self.on_param_changed(p['key'], norm, p)
            )
            slider.setEnabled(False)
            param_layout.addWidget(slider, alignment=Qt.AlignHCenter)
            
            self.sliders[param['key']] = slider
            self.slider_labels[param['key']] = lbl
            params_layout.addWidget(param_widget)
        
        params_layout.addSpacing(5)
        
        # Buttons column
        buttons_widget = QWidget()
        buttons_widget.setFixedWidth(SIZES['buttons_column_width'])
        buttons_layout = QVBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(3)
        
        # Filter type - CycleButton
        self.filter_btn = CycleButton(FILTER_TYPES, initial_index=0)
        self.filter_btn.setFixedSize(*SIZES['button_medium'])
        self.filter_btn.setFont(QFont(MONO_FONT, FONT_SIZES['small'], QFont.Bold))
        self.filter_btn.setStyleSheet(button_style('enabled'))
        self.filter_btn.wrap = True
        self.filter_btn.value_changed.connect(self.on_filter_changed)
        self.filter_btn.setEnabled(False)
        self.filter_btn.setToolTip("Filter Type: LP / HP / BP")
        buttons_layout.addWidget(self.filter_btn)
        
        # ENV source - CycleButton (OFF/CLK/MIDI)
        self.env_btn = CycleButton(ENV_SOURCES, initial_index=0)
        self.env_btn.setFixedSize(*SIZES['button_medium'])
        self.env_btn.setFont(QFont(MONO_FONT, FONT_SIZES['tiny'], QFont.Bold))
        self.env_btn.setStyleSheet(button_style('disabled'))
        self.env_btn.wrap = True
        self.env_btn.value_changed.connect(self.on_env_source_changed)
        self.env_btn.setEnabled(False)
        self.env_btn.setToolTip("Envelope source: OFF (drone), CLK (clock), MIDI")
        buttons_layout.addWidget(self.env_btn)
        
        # CLK rate - CycleButton
        self.rate_btn = CycleButton(CLOCK_RATES, initial_index=CLOCK_DEFAULT_INDEX)
        self.rate_btn.setFixedSize(*SIZES['button_medium'])
        self.rate_btn.setFont(QFont(MONO_FONT, FONT_SIZES['tiny']))
        self.rate_btn.setStyleSheet(button_style('inactive'))
        self.rate_btn.wrap = False
        self.rate_btn.value_changed.connect(self.on_rate_changed)
        self.rate_btn.setEnabled(False)
        self.rate_btn.setToolTip("Clock rate\n↑ faster: x8, x4, x2\n↓ slower: /2, /4, /8, /16")
        buttons_layout.addWidget(self.rate_btn)
        
        # Separator/spacer
        buttons_layout.addSpacing(6)
        
        # MIDI channel selector
        self.midi_btn = CycleButton(MIDI_CHANNELS, initial_index=0)
        self.midi_btn.setFixedSize(*SIZES['button_medium'])
        self.midi_btn.setFont(QFont(MONO_FONT, FONT_SIZES['tiny'], QFont.Bold))
        self.midi_btn.setStyleSheet(midi_channel_style(False))
        self.midi_btn.wrap = True
        self.midi_btn.value_changed.connect(self.on_midi_channel_changed)
        self.midi_btn.setToolTip("MIDI Input Channel (OFF or 1-16)")
        buttons_layout.addWidget(self.midi_btn)
        
        # Mute/Gate row - small buttons side by side
        mute_gate_row = QHBoxLayout()
        mute_gate_row.setSpacing(2)
        mute_gate_row.setContentsMargins(0, 0, 0, 0)
        
        # Mute button
        self.mute_btn = QPushButton("M")
        self.mute_btn.setFixedSize(18, 18)
        self.mute_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro'], QFont.Bold))
        self.mute_btn.setStyleSheet(mute_button_style(False))
        self.mute_btn.clicked.connect(self.toggle_mute)
        self.mute_btn.setToolTip("Mute Generator")
        mute_gate_row.addWidget(self.mute_btn)
        
        # Gate indicator LED
        self.gate_led = QLabel()
        self.gate_led.setFixedSize(18, 18)
        self.gate_led.setStyleSheet(gate_indicator_style(False))
        self.gate_led.setToolTip("Gate Activity")
        mute_gate_row.addWidget(self.gate_led)
        
        buttons_layout.addLayout(mute_gate_row)
        
        buttons_layout.addStretch()
        params_layout.addWidget(buttons_widget)
        
        params_outer.addLayout(params_layout)
        
        layout.addWidget(params_frame)
        
        # Status
        status_layout = QHBoxLayout()
        status_layout.setSpacing(15)
        
        self.audio_indicator = QLabel("🔇 Audio")
        self.audio_indicator.setFont(QFont(FONT_FAMILY, FONT_SIZES['small']))
        self.audio_indicator.setStyleSheet(f"color: {COLORS['audio_off']};")
        status_layout.addWidget(self.audio_indicator)
        
        self.midi_indicator = QLabel("🎹 MIDI")
        self.midi_indicator.setFont(QFont(FONT_FAMILY, FONT_SIZES['small']))
        self.midi_indicator.setStyleSheet(f"color: {COLORS['midi_off']};")
        status_layout.addWidget(self.midi_indicator)
        
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
    def update_style(self):
        """Update appearance based on state."""
        if self.generator_type == "Empty":
            border_color = COLORS['border']
            bg_color = COLORS['background']
            type_color = COLORS['text']
        elif self.active:
            border_color = COLORS['border_active']
            bg_color = COLORS['active_bg']
            type_color = COLORS['enabled_text']  # Green when active
        else:
            border_color = COLORS['border_light']
            bg_color = COLORS['background_light']
            type_color = COLORS['text']
            
        self.setStyleSheet(f"""
            GeneratorSlot {{
                border: 2px solid {border_color};
                border-radius: 6px;
                background-color: {bg_color};
            }}
        """)
        
        # Update generator name color
        self.type_btn.setStyleSheet(f"""
            QPushButton {{
                color: {type_color};
                background: transparent;
                border: none;
                text-align: right;
                padding: 2px 4px;
            }}
            QPushButton:hover {{
                color: {COLORS['enabled_text']};
            }}
        """)
        
    def update_env_style(self):
        """Update ENV button styles based on state."""
        if self.env_source == 0:  # OFF
            self.env_btn.setStyleSheet(button_style('disabled'))
            self.rate_btn.setEnabled(False)
            self.rate_btn.setStyleSheet(button_style('inactive'))
        elif self.env_source == 1:  # CLK
            self.env_btn.setStyleSheet(button_style('enabled'))
            self.rate_btn.setEnabled(True and self.generator_type != "Empty")
            self.rate_btn.setStyleSheet(button_style('submenu'))
        else:  # MIDI
            self.env_btn.setStyleSheet(button_style('enabled'))
            self.rate_btn.setEnabled(False)  # Rate doesn't matter for MIDI
            self.rate_btn.setStyleSheet(button_style('inactive'))
        
    def set_generator_type(self, gen_type):
        """Change generator type.
        
        IMPORTANT: Slot settings (ENV source, clock rate, MIDI channel) are PRESERVED
        when changing generator type. The slot is like a Eurorack slot - swapping the
        module doesn't change the trigger/clock patching. Settings are reapplied to
        ensure the new generator receives them.
        """
        self.generator_type = gen_type
        self.type_btn.blockSignals(True)
        self.type_btn.set_value(gen_type)
        self.type_btn.blockSignals(False)
        
        enabled = gen_type != "Empty"
        pitch_target = get_generator_pitch_target(gen_type)
        
        # REAPPLY (not reset) ENV source - slot remembers its setting
        self.env_source_changed.emit(self.slot_id, self.env_source)
        
        # REAPPLY clock rate
        current_rate = self.rate_btn.get_value()
        from src.config import CLOCK_RATE_INDEX
        self.clock_rate_changed.emit(self.slot_id, current_rate)
        
        # REAPPLY MIDI channel
        self.midi_channel_changed.emit(self.slot_id, self.midi_channel)
        
        # Legacy - keep clock_enabled in sync
        self.clock_enabled = self.env_source > 0
        self.clock_enabled_changed.emit(self.slot_id, self.clock_enabled)
        
        # REAPPLY filter type (also sticky per slot)
        current_filter = self.filter_btn.get_value()
        self.filter_type_changed.emit(self.slot_id, current_filter)
        
        # Reset standard sliders to defaults and send values
        for key, slider in self.sliders.items():
            param = next((p for p in GENERATOR_PARAMS if p['key'] == key), None)
            if param:
                default_val = int(param['default'] * 1000)
                # Force send even if value is same (bus might have old value)
                slider.blockSignals(True)
                slider.setValue(default_val)
                slider.blockSignals(False)
                # Always emit to update SuperCollider
                real_value = map_value(param['default'], param)
                self.parameter_changed.emit(self.slot_id, key, real_value)
            
            if key == 'frequency' and pitch_target is not None:
                # FRQ disabled when pitch_target points to custom param
                slider.setEnabled(False)
            else:
                slider.setEnabled(enabled)
        
        # Update FRQ label to show it's overridden
        if 'frequency' in self.slider_labels:
            if pitch_target is not None:
                self.slider_labels['frequency'].setStyleSheet(f"color: {COLORS['text_dim']};")
            else:
                self.slider_labels['frequency'].setStyleSheet(f"color: {COLORS['text']};")
        
        self.filter_btn.setEnabled(enabled)
        self.env_btn.setEnabled(enabled)
        self.update_env_style()
        self.update_style()
        
        # Update custom params for this generator (also resets to defaults)
        self.update_custom_params(gen_type)
    
    def update_custom_params(self, gen_type):
        """Update custom param sliders for current generator type."""
        custom_params = get_generator_custom_params(gen_type)
        pitch_target = get_generator_pitch_target(gen_type)
        midi_retrig = get_generator_midi_retrig(gen_type)
        retrig_param_index = get_generator_retrig_param_index(gen_type)
        
        for i in range(MAX_CUSTOM_PARAMS):
            if i < len(custom_params):
                param = custom_params[i]
                label_text = param['label']
                
                # Add pitch indicator if this is the pitch target
                if pitch_target == i:
                    label_text = f"♪{label_text}"
                    self.custom_labels[i].setStyleSheet(f"color: {COLORS['enabled_text']};")
                else:
                    self.custom_labels[i].setStyleSheet(f"color: {COLORS['text']};")
                
                self.custom_labels[i].setText(label_text)
                from src.config import format_value
                # Block signals while setting up
                self.custom_sliders[i].blockSignals(True)
                self.custom_sliders[i].set_param_config(param, format_value)
                self.custom_sliders[i].blockSignals(False)
                self.custom_sliders[i].setToolTip(param.get('tooltip', ''))
                
                # Grey out RTG param in MIDI mode for midi_retrig generators
                if midi_retrig and i == retrig_param_index and self.env_source == 2:
                    self.custom_sliders[i].setEnabled(False)
                    self.custom_labels[i].setStyleSheet(f"color: {COLORS['text_dim']};")
                else:
                    self.custom_sliders[i].setEnabled(True)
                
                # Force send default value to SuperCollider
                default = param.get('default', 0.5)
                real_value = map_value(default, param)
                self.custom_parameter_changed.emit(self.slot_id, i, real_value)
            else:
                self.custom_labels[i].setText(f"P{i+1}")
                self.custom_labels[i].setStyleSheet(f"color: {COLORS['text_dim']};")
                self.custom_sliders[i].blockSignals(True)
                self.custom_sliders[i].set_param_config(None)
                self.custom_sliders[i].setValue(500)  # Reset to midpoint
                self.custom_sliders[i].blockSignals(False)
                self.custom_sliders[i].setToolTip("")
                self.custom_sliders[i].setEnabled(False)
    
    def _update_retrig_param_state(self):
        """Update RTG param enable state based on env_source and generator type."""
        midi_retrig = get_generator_midi_retrig(self.generator_type)
        retrig_param_index = get_generator_retrig_param_index(self.generator_type)
        
        if midi_retrig and retrig_param_index is not None:
            # Grey out RTG in MIDI mode, enable otherwise
            if self.env_source == 2:  # MIDI
                self.custom_sliders[retrig_param_index].setEnabled(False)
                self.custom_labels[retrig_param_index].setStyleSheet(f"color: {COLORS['text_dim']};")
            else:
                self.custom_sliders[retrig_param_index].setEnabled(True)
                self.custom_labels[retrig_param_index].setStyleSheet(f"color: {COLORS['text']};")
        
    def set_active(self, active):
        """Set active state."""
        self.active = active
        self.update_style()
        
    def set_audio_status(self, active):
        """Update audio indicator."""
        if active:
            self.audio_indicator.setText("🔊 Audio")
            self.audio_indicator.setStyleSheet(f"color: {COLORS['audio_on']};")
        else:
            self.audio_indicator.setText("🔇 Audio")
            self.audio_indicator.setStyleSheet(f"color: {COLORS['audio_off']};")
            
    def set_midi_status(self, active):
        """Update MIDI indicator."""
        if active:
            self.midi_indicator.setText("🎹 MIDI")
            self.midi_indicator.setStyleSheet(f"color: {COLORS['midi_on']};")
        else:
            self.midi_indicator.setText("🎹 MIDI")
            self.midi_indicator.setStyleSheet(f"color: {COLORS['midi_off']};")
            
    def on_filter_changed(self, filter_type):
        """Handle filter button change."""
        logger.gen(self.slot_id, f"filter: {filter_type}")
        self.filter_type_changed.emit(self.slot_id, filter_type)
    
    def on_generator_type_changed(self, gen_type):
        """Handle generator type change from CycleButton."""
        self.generator_type = gen_type
        logger.gen(self.slot_id, f"type: {gen_type}")
        self.generator_changed.emit(self.slot_id, gen_type)
        
    def on_env_source_changed(self, source_str):
        """Handle ENV source button change."""
        self.env_source = ENV_SOURCE_INDEX[source_str]
        self.update_env_style()
        self.env_source_changed.emit(self.slot_id, self.env_source)
        
        # Auto-set MIDI channel when switching to MIDI mode
        if self.env_source == 2:  # MIDI
            # Set MIDI channel to match generator slot (1-8)
            self.midi_channel = self.slot_id
            self.midi_btn.blockSignals(True)
            self.midi_btn.set_index(self.slot_id)  # Index 0=OFF, 1-16=channels
            self.midi_btn.blockSignals(False)
            self.midi_btn.setStyleSheet(midi_channel_style(True))
            self.midi_channel_changed.emit(self.slot_id, self.midi_channel)
        
        # Update RTG param enable state for midi_retrig generators
        self._update_retrig_param_state()
        
        # Legacy - keep clock_enabled in sync (ON if CLK or MIDI)
        self.clock_enabled = self.env_source > 0
        self.clock_enabled_changed.emit(self.slot_id, self.clock_enabled)
        
    def on_rate_changed(self, rate):
        """Handle rate button change."""
        self.clock_rate_changed.emit(self.slot_id, rate)
        
    def on_param_changed(self, param_key, normalized, param_config):
        """Handle parameter change - emit real mapped value."""
        real_value = map_value(normalized, param_config)
        self.parameter_changed.emit(self.slot_id, param_key, real_value)
    
    def on_custom_param_changed(self, param_index, normalized):
        """Handle custom parameter change - emit real mapped value."""
        custom_params = get_generator_custom_params(self.generator_type)
        if param_index < len(custom_params):
            param_config = custom_params[param_index]
            real_value = map_value(normalized, param_config)
            self.custom_parameter_changed.emit(self.slot_id, param_index, real_value)
    
    def toggle_mute(self):
        """Toggle mute state."""
        self.muted = not self.muted
        self.mute_btn.setStyleSheet(mute_button_style(self.muted))
        self.mute_changed.emit(self.slot_id, self.muted)
    
    def on_midi_channel_changed(self, channel_str):
        """Handle MIDI channel change."""
        if channel_str == "OFF":
            self.midi_channel = 0
            self.midi_btn.setStyleSheet(midi_channel_style(False))
        else:
            self.midi_channel = int(channel_str)
            self.midi_btn.setStyleSheet(midi_channel_style(True))
        self.midi_channel_changed.emit(self.slot_id, self.midi_channel)
    
    def flash_gate(self):
        """Flash the gate LED (call when gate trigger received)."""
        self.gate_led.setStyleSheet(gate_indicator_style(True))
        self.gate_timer.start(80)  # LED on for 80ms
    
    def _gate_off(self):
        """Turn off gate LED after flash."""
        self.gate_led.setStyleSheet(gate_indicator_style(False))
