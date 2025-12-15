"""
Generator Slot Component
Individual generator with base parameters
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

from .theme import (COLORS, button_style, FONT_FAMILY, FONT_SIZES,
                    mute_button_style, gate_indicator_style, midi_channel_style)
from .generator_slot_builder import build_slot_ui
from src.config import (
    GENERATOR_PARAMS, map_value,
    get_generator_custom_params, get_generator_pitch_target,
    get_generator_midi_retrig, get_generator_retrig_param_index,
    ENV_SOURCE_INDEX
)
from src.utils.logger import logger


class GeneratorSlot(QWidget):
    """A single generator slot with base parameters."""
    
    # Signals
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
        build_slot_ui(self)  # UI construction delegated to builder
        self.update_style()
    
    # -------------------------------------------------------------------------
    # Style Updates
    # -------------------------------------------------------------------------
    
    def update_style(self):
        """Update appearance based on state."""
        if self.generator_type == "Empty":
            border_color = COLORS['border']
            bg_color = COLORS['background']
            type_color = COLORS['text']
        elif self.active:
            border_color = COLORS['border_active']
            bg_color = COLORS['active_bg']
            type_color = COLORS['enabled_text']
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
            self.rate_btn.setEnabled(False)
            self.rate_btn.setStyleSheet(button_style('inactive'))
    
    # -------------------------------------------------------------------------
    # State Management
    # -------------------------------------------------------------------------
    
    def set_generator_type(self, gen_type):
        """Change generator type.
        
        IMPORTANT: Slot settings (ENV source, clock rate, MIDI channel) are PRESERVED
        when changing generator type. The slot is like a Eurorack slot - swapping the
        module doesn't change the trigger/clock patching.
        """
        self.generator_type = gen_type
        self.type_btn.blockSignals(True)
        self.type_btn.set_value(gen_type)
        self.type_btn.blockSignals(False)
        
        enabled = gen_type != "Empty"
        pitch_target = get_generator_pitch_target(gen_type)
        
        # REAPPLY (not reset) slot settings
        self.env_source_changed.emit(self.slot_id, self.env_source)
        
        current_rate = self.rate_btn.get_value()
        self.clock_rate_changed.emit(self.slot_id, current_rate)
        
        self.midi_channel_changed.emit(self.slot_id, self.midi_channel)
        
        # Legacy
        self.clock_enabled = self.env_source > 0
        self.clock_enabled_changed.emit(self.slot_id, self.clock_enabled)
        
        current_filter = self.filter_btn.get_value()
        self.filter_type_changed.emit(self.slot_id, current_filter)
        
        # Reset standard sliders to defaults and send values
        for key, slider in self.sliders.items():
            param = next((p for p in GENERATOR_PARAMS if p['key'] == key), None)
            if param:
                default_val = int(param['default'] * 1000)
                slider.blockSignals(True)
                slider.setValue(default_val)
                slider.blockSignals(False)
                real_value = map_value(param['default'], param)
                self.parameter_changed.emit(self.slot_id, key, real_value)
            
            if key == 'frequency' and pitch_target is not None:
                slider.setEnabled(False)
            else:
                slider.setEnabled(enabled)
        
        # Update FRQ label style
        if 'frequency' in self.slider_labels:
            if pitch_target is not None:
                self.slider_labels['frequency'].setStyleSheet(f"color: {COLORS['text_dim']};")
            else:
                self.slider_labels['frequency'].setStyleSheet(f"color: {COLORS['text']};")
        
        self.filter_btn.setEnabled(enabled)
        self.env_btn.setEnabled(enabled)
        self.update_env_style()
        self.update_style()
        
        self.update_custom_params(gen_type)
    
    def update_custom_params(self, gen_type):
        """Update custom param sliders for current generator type."""
        custom_params = get_generator_custom_params(gen_type)
        pitch_target = get_generator_pitch_target(gen_type)
        midi_retrig = get_generator_midi_retrig(gen_type)
        retrig_param_index = get_generator_retrig_param_index(gen_type)
        
        from src.config import MAX_CUSTOM_PARAMS, format_value
        
        for i in range(MAX_CUSTOM_PARAMS):
            if i < len(custom_params):
                param = custom_params[i]
                label_text = param['label']
                
                if pitch_target == i:
                    label_text = f"♪{label_text}"
                    self.custom_labels[i].setStyleSheet(f"color: {COLORS['enabled_text']};")
                else:
                    self.custom_labels[i].setStyleSheet(f"color: {COLORS['text']};")
                
                self.custom_labels[i].setText(label_text)
                self.custom_sliders[i].blockSignals(True)
                self.custom_sliders[i].set_param_config(param, format_value)
                self.custom_sliders[i].blockSignals(False)
                self.custom_sliders[i].setToolTip(param.get('tooltip', ''))
                
                if midi_retrig and i == retrig_param_index and self.env_source == 2:
                    self.custom_sliders[i].setEnabled(False)
                    self.custom_labels[i].setStyleSheet(f"color: {COLORS['text_dim']};")
                else:
                    self.custom_sliders[i].setEnabled(True)
                
                default = param.get('default', 0.5)
                real_value = map_value(default, param)
                self.custom_parameter_changed.emit(self.slot_id, i, real_value)
            else:
                self.custom_labels[i].setText(f"P{i+1}")
                self.custom_labels[i].setStyleSheet(f"color: {COLORS['text_dim']};")
                self.custom_sliders[i].blockSignals(True)
                self.custom_sliders[i].set_param_config(None)
                self.custom_sliders[i].setValue(500)
                self.custom_sliders[i].blockSignals(False)
                self.custom_sliders[i].setToolTip("")
                self.custom_sliders[i].setEnabled(False)
    
    def _update_retrig_param_state(self):
        """Update RTG param enable state based on env_source and generator type."""
        midi_retrig = get_generator_midi_retrig(self.generator_type)
        retrig_param_index = get_generator_retrig_param_index(self.generator_type)
        
        if midi_retrig and retrig_param_index is not None:
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
        """Update audio indicator (removed - stub for compatibility)."""
        pass
            
    def set_midi_status(self, active):
        """Update MIDI indicator (removed - stub for compatibility)."""
        pass
    
    # -------------------------------------------------------------------------
    # Event Handlers
    # -------------------------------------------------------------------------
    
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
            self.midi_channel = self.slot_id
            self.midi_btn.blockSignals(True)
            self.midi_btn.set_index(self.slot_id)
            self.midi_btn.blockSignals(False)
            self.midi_btn.setStyleSheet(midi_channel_style(True))
            self.midi_channel_changed.emit(self.slot_id, self.midi_channel)
        
        self._update_retrig_param_state()
        
        # Legacy
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
        self.gate_timer.start(80)
    
    def _gate_off(self):
        """Turn off gate LED after flash."""
        self.gate_led.setStyleSheet(gate_indicator_style(False))
