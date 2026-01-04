"""
Generator Slot v3 - Flat absolute positioning with full functionality
Styled like ModulatorSlot - green accent border when loaded
"""
from PyQt5.QtWidgets import QWidget, QLabel, QFrame
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPainter, QPen, QPainterPath, QColor

from .widgets import DragSlider, CycleButton, MiniKnob
from .theme import (COLORS, FONT_FAMILY, MONO_FONT, FONT_SIZES, button_style,
                    mute_button_style, gate_indicator_style, midi_channel_style)

from src.config import (
    GENERATOR_PARAMS, MAX_CUSTOM_PARAMS, GENERATOR_CYCLE,
    get_generator_custom_params, get_generator_pitch_target,
    get_generator_midi_retrig, get_generator_retrig_param_index,
    CLOCK_RATES, FILTER_TYPES, ENV_SOURCES, ENV_SOURCE_INDEX,
    TRANSPOSE_SEMITONES, map_value, format_value
)
from src.utils.logger import logger


class GenScope(QWidget):
    """Simple waveform display for generator slots."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.waveform = "sine"
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            background-color: {COLORS['background']};
            border: 1px solid {COLORS['border']};
        """)

    def set_waveform(self, generator_type):
        """Set waveform based on generator type."""
        wave_map = {
            'Empty': 'flat',
            'Sine': 'sine', 'Sub': 'sine', 'Hymn': 'sine', 'Choir': 'sine',
            'Saw': 'saw', 'Hive': 'saw', 'Swarm': 'saw',
            'Square': 'square', 'Pulse': 'square',
            'Noise': 'noise', 'Wind': 'noise', 'Rain': 'noise',
            'FM': 'fm', 'Bell': 'fm',
        }
        for key, wave in wave_map.items():
            if key.lower() in generator_type.lower():
                self.waveform = wave
                break
        else:
            self.waveform = 'sine'
        self.update()

    def paintEvent(self, event):
        import math
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        mid_y = h // 2
        margin = 4
        draw_w = w - margin * 2
        draw_h = h - margin * 2

        pen = QPen(QColor(COLORS.get('accent_generator', '#00ff66')))
        pen.setWidth(1)
        painter.setPen(pen)

        if self.waveform == 'flat':
            painter.drawLine(margin, mid_y, w - margin, mid_y)

        elif self.waveform == 'sine':
            path = QPainterPath()
            for i in range(draw_w):
                x = margin + i
                y = mid_y - int(math.sin(i * 4 * math.pi / draw_w) * (draw_h // 2 - 2))
                if i == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            painter.drawPath(path)

        elif self.waveform == 'saw':
            path = QPainterPath()
            teeth = 3
            tooth_w = draw_w // teeth
            for t in range(teeth):
                x1 = margin + t * tooth_w
                x2 = margin + (t + 1) * tooth_w
                path.moveTo(x1, mid_y + draw_h // 2 - 2)
                path.lineTo(x2, mid_y - draw_h // 2 + 2)
                path.moveTo(x2, mid_y + draw_h // 2 - 2)
            painter.drawPath(path)

        elif self.waveform == 'square':
            path = QPainterPath()
            step = draw_w // 4
            y_top = mid_y - draw_h // 2 + 2
            y_bot = mid_y + draw_h // 2 - 2
            path.moveTo(margin, y_top)
            path.lineTo(margin + step, y_top)
            path.lineTo(margin + step, y_bot)
            path.lineTo(margin + step * 2, y_bot)
            path.lineTo(margin + step * 2, y_top)
            path.lineTo(margin + step * 3, y_top)
            path.lineTo(margin + step * 3, y_bot)
            path.lineTo(margin + step * 4, y_bot)
            painter.drawPath(path)

        elif self.waveform == 'noise':
            import random
            random.seed(42)
            path = QPainterPath()
            path.moveTo(margin, mid_y)
            for i in range(0, draw_w, 2):
                x = margin + i
                y = mid_y + random.randint(-draw_h // 2 + 2, draw_h // 2 - 2)
                path.lineTo(x, y)
            painter.drawPath(path)

        elif self.waveform == 'fm':
            path = QPainterPath()
            for i in range(draw_w):
                x = margin + i
                mod = math.sin(i * 12 * math.pi / draw_w) * 0.3
                y = mid_y - int(math.sin(i * 4 * math.pi / draw_w + mod * 3) * (draw_h // 2 - 2))
                if i == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            painter.drawPath(path)


# =============================================================================
# LAYOUT - All positions in one place
# =============================================================================
SLOT_LAYOUT = {
    'slot_width': 180,
    'slot_height': 326,

    # Header
    'gen_label_x': 5, 'gen_label_y': 5,
    'gen_label_w': 40, 'gen_label_h': 20,
    'selector_x': 66, 'selector_y': 2,
    'selector_w': 110, 'selector_h': 22,

    # Slider sizing
    'slider_w': 18, 'slider_h': 100, 'slider_label_h': 12,

    # Custom sliders P1-P5
    'p1_x': 5, 'p1_y': 32,
    'p2_x': 30, 'p2_y': 32,
    'p3_x': 54, 'p3_y': 32,
    'p4_x': 78, 'p4_y': 32,
    'p5_x': 102, 'p5_y': 32,

    # Standard sliders
    'frq_x': 6, 'frq_y': 156,
    'cut_x': 30, 'cut_y': 156,
    'res_x': 54, 'res_y': 156,
    'atk_x': 78, 'atk_y': 156,
    'dec_x': 102, 'dec_y': 156,

    # Buttons
    'btn_w': 34, 'btn_h': 22,
    'btn_x': 134,
    'btn_filter_y': 32,
    'btn_env_y': 58,
    'btn_rate_y': 82,
    'btn_trans_y': 106,
    'btn_midi_y': 130,
    'btn_mute_y': 154,

    # Gate & Portamento
    'gate_x': 134, 'gate_y': 178, 'gate_w': 34, 'gate_h': 14,
    'port_x': 142, 'port_y': 194, 'port_w': 18, 'port_h': 80,
}

L = SLOT_LAYOUT


class GeneratorSlot(QWidget):
    """Generator slot with flat absolute positioning and full functionality."""
    
    # Signals (same as v1)
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
    transpose_changed = pyqtSignal(int, int)  # slot_id, semitones
    portamento_changed = pyqtSignal(int, float)  # slot_id, value (0-1)
    
    def __init__(self, slot_id, generator_type="Empty", parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        
        self.slot_id = slot_id
        self.setObjectName(f"gen{slot_id}_slot")
        self.generator_type = generator_type
        self.active = False
        self.clock_enabled = False  # Legacy
        self.env_source = 0  # 0=OFF, 1=CLK, 2=MIDI
        self.muted = False
        self.midi_channel = 0  # 0 = OFF, 1-16 = channels
        self.transpose = 0  # Semitones (-24 to +24)
        self.portamento = 0  # Portamento time (0-1)
        
        self.setFixedSize(L['slot_width'], L['slot_height'])
        
        # Gate indicator flash timer
        self.gate_timer = QTimer()
        self.gate_timer.timeout.connect(self._gate_off)
        self.gate_timer.setSingleShot(True)
        
        # Storage
        self.sliders = {}
        self.slider_labels = {}
        self.custom_sliders = []
        self.custom_labels = []
        
        self._build_ui()
        self.update_style()
    
    # =========================================================================
    # UI Building
    # =========================================================================
    
    def _build_ui(self):
        """Build all widgets with absolute positioning."""
        
        # ----- HEADER -----
        self.id_label = QLabel(f"GEN {self.slot_id}", self)
        self.id_label.setFont(QFont(FONT_FAMILY, 9, QFont.Bold))
        self.id_label.setStyleSheet(f"color: {COLORS['text_bright']};")
        self.id_label.setGeometry(L['gen_label_x'], L['gen_label_y'], 
                                   L['gen_label_w'], L['gen_label_h'])
        
        self.type_btn = CycleButton(GENERATOR_CYCLE, parent=self)
        self.type_btn.setGeometry(L['selector_x'], L['selector_y'],
                                   L['selector_w'], L['selector_h'])
        self.type_btn.value_changed.connect(self.on_generator_type_changed)
        self.type_btn.setFont(QFont(MONO_FONT, FONT_SIZES["small"]))
        self.type_btn.setStyleSheet(button_style("submenu"))

        # ----- SEPARATOR -----
        self.separator = QFrame(self)
        self.separator.setGeometry(4, 26, L['slot_width'] - 8, 1)
        self.separator.setStyleSheet(f"background-color: {COLORS['text_bright']};")

        # ----- CUSTOM SLIDERS P1-P5 -----
        custom_positions = [
            (L['p1_x'], L['p1_y']), (L['p2_x'], L['p2_y']), (L['p3_x'], L['p3_y']),
            (L['p4_x'], L['p4_y']), (L['p5_x'], L['p5_y']),
        ]
        for i in range(MAX_CUSTOM_PARAMS):
            x, y = custom_positions[i]
            lbl = QLabel(f"P{i+1}", self)
            lbl.setFont(QFont(FONT_FAMILY, 7))
            lbl.setStyleSheet(f"color: {COLORS['text_dim']};")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setGeometry(x, y, L['slider_w'], L['slider_label_h'])
            self.custom_labels.append(lbl)
            
            slider = DragSlider(parent=self)
            slider.setRange(0, 1000)
            slider.setValue(500)
            slider.setGeometry(x, y + L['slider_label_h'], L['slider_w'], L['slider_h'])
            slider.setObjectName(f"gen{self.slot_id}_custom{i}")
            slider.valueChanged.connect(lambda v, idx=i: self.on_custom_param_changed(idx, v / 1000.0))
            slider.setEnabled(False)
            self.custom_sliders.append(slider)
        
        # ----- STANDARD SLIDERS -----
        std_params = ['frequency', 'cutoff', 'resonance', 'attack', 'decay']
        std_labels = ['FRQ', 'CUT', 'RES', 'ATK', 'DEC']
        std_positions = [
            (L['frq_x'], L['frq_y']), (L['cut_x'], L['cut_y']), (L['res_x'], L['res_y']),
            (L['atk_x'], L['atk_y']), (L['dec_x'], L['dec_y']),
        ]
        
        for key, label_text, (x, y) in zip(std_params, std_labels, std_positions):
            lbl = QLabel(label_text, self)
            lbl.setFont(QFont(FONT_FAMILY, 7))
            lbl.setStyleSheet(f"color: {COLORS['text']};")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setGeometry(x, y, L['slider_w'], L['slider_label_h'])
            self.slider_labels[key] = lbl
            
            slider = DragSlider(parent=self)
            slider.setRange(0, 1000)
            slider.setValue(500)
            slider.setGeometry(x, y + L['slider_label_h'], L['slider_w'], L['slider_h'])
            slider.setObjectName(f"gen{self.slot_id}_{key}")
            
            # Find param config and set it
            param_config = next((p for p in GENERATOR_PARAMS if p['key'] == key), None)
            if param_config:
                slider.set_param_config(param_config, format_value)
                slider.valueChanged.connect(
                    lambda v, k=key, pc=param_config: self.on_param_changed(k, v / 1000.0, pc)
                )
            
            self.sliders[key] = slider
        
        # ----- BUTTONS -----
        btn_x, btn_w, btn_h = L['btn_x'], L['btn_w'], L['btn_h']
        
        self.filter_btn = CycleButton(FILTER_TYPES, parent=self)
        self.filter_btn.setGeometry(btn_x, L['btn_filter_y'], btn_w, btn_h)
        self.filter_btn.value_changed.connect(self.on_filter_changed)
        self.filter_btn.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        self.filter_btn.setStyleSheet(button_style('submenu'))
        
        self.env_btn = CycleButton(ENV_SOURCES, parent=self)
        self.env_btn.setGeometry(btn_x, L['btn_env_y'], btn_w, btn_h)
        self.env_btn.value_changed.connect(self.on_env_source_changed)
        self.env_btn.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        
        self.rate_btn = CycleButton(CLOCK_RATES, parent=self)
        self.rate_btn.setGeometry(btn_x, L['btn_rate_y'], btn_w, btn_h)
        self.rate_btn.value_changed.connect(self.on_rate_changed)
        self.rate_btn.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        self.rate_btn.set_index(4)  # Default to 1/4
        
        self.transpose_btn = CycleButton([str(s) for s in TRANSPOSE_SEMITONES], parent=self)
        self.transpose_btn.setGeometry(btn_x, L['btn_trans_y'], btn_w, btn_h)
        self.transpose_btn.value_changed.connect(self.on_transpose_changed)
        self.transpose_btn.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        self.transpose_btn.setStyleSheet(button_style('submenu'))
        self.transpose_btn.set_index(2)  # Default to 0 semitones
        
        midi_values = ['OFF'] + [str(i) for i in range(1, 17)]
        self.midi_btn = CycleButton(midi_values, parent=self)
        self.midi_btn.setGeometry(btn_x, L['btn_midi_y'], btn_w, btn_h)
        self.midi_btn.value_changed.connect(self.on_midi_channel_changed)
        self.midi_btn.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        self.midi_btn.setStyleSheet(midi_channel_style(False))
        
        self.mute_btn = CycleButton(['M', 'M'], parent=self)
        self.mute_btn.setGeometry(btn_x, L['btn_mute_y'], btn_w, btn_h)
        self.mute_btn.value_changed.connect(self.toggle_mute)
        self.mute_btn.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        self.mute_btn.setStyleSheet(mute_button_style(False))
        
        # ----- GATE INDICATOR -----
        self.gate_led = QLabel(self)
        self.gate_led.setGeometry(L['gate_x'], L['gate_y'], L['gate_w'], L['gate_h'])
        self.gate_led.setStyleSheet(gate_indicator_style(False))

        # ----- PORTAMENTO -----
        self.port_label = QLabel("PORT", self)
        self.port_label.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        self.port_label.setAlignment(Qt.AlignCenter)
        self.port_label.setStyleSheet(f"color: {COLORS['text_bright']};")
        self.port_label.setGeometry(L['port_x'] - 2, L['port_y'], 26, 12)

        self.portamento_knob = MiniKnob()
        self.portamento_knob.setParent(self)
        self.portamento_knob.setFixedSize(26, 26)
        self.portamento_knob.move(L['port_x'] - 2, L['port_y'] + 14)
        self.portamento_knob.setObjectName(f"gen{self.slot_id}_port")
        self.portamento_knob.setToolTip("Portamento")
        self.portamento_knob.valueChanged.connect(self.on_portamento_changed)
        
        # ----- SCOPE -----
        self.scope = GenScope(self)
        self.scope.setGeometry(5, L['slot_height'] - 55, 120, 50)
        
        # Initial env style
        self.update_env_style()
    
    # =========================================================================
    # State Management
    # =========================================================================
    
    def get_state(self) -> dict:
        """Get current slot state for preset save."""
        params = {}
        for key, slider in self.sliders.items():
            params[key] = slider.value() / 1000.0
        
        for i in range(MAX_CUSTOM_PARAMS):
            params[f"custom_{i}"] = self.custom_sliders[i].value() / 1000.0
        
        return {
            "generator": self.generator_type if self.generator_type != "Empty" else None,
            "params": params,
            "filter_type": self.filter_btn.index,
            "env_source": self.env_source,
            "clock_rate": self.rate_btn.index,
            "midi_channel": self.midi_channel,
            "transpose": self.transpose_btn.index,
            "portamento": self.portamento,
        }

    def set_state(self, state: dict):
        """Apply state from preset load."""
        gen = state.get("generator")
        
        # Set generator type first (this resets params to defaults)
        if gen:
            self.set_generator_type(gen)
            self.generator_changed.emit(self.slot_id, gen)
        else:
            self.set_generator_type("Empty")
            self.generator_changed.emit(self.slot_id, "Empty")
            return

        # Now override params with saved values
        params = state.get("params", {})
        
        # Standard params
        for key, slider in self.sliders.items():
            if key in params:
                value = params[key]
                slider.blockSignals(True)
                slider.setValue(int(value * 1000))
                slider.blockSignals(False)
                param_config = next((p for p in GENERATOR_PARAMS if p['key'] == key), None)
                if param_config:
                    real_value = map_value(value, param_config)
                    self.parameter_changed.emit(self.slot_id, key, real_value)
        
        # Custom params
        custom_params = get_generator_custom_params(self.generator_type)
        for i in range(MAX_CUSTOM_PARAMS):
            key = f"custom_{i}"
            if key in params:
                value = params[key]
                self.custom_sliders[i].blockSignals(True)
                self.custom_sliders[i].setValue(int(value * 1000))
                self.custom_sliders[i].blockSignals(False)
                if i < len(custom_params):
                    real_value = map_value(value, custom_params[i])
                    self.custom_parameter_changed.emit(self.slot_id, i, real_value)
        
        # Filter type
        ft = state.get("filter_type", 0)
        self.filter_btn.blockSignals(True)
        self.filter_btn.set_index(ft)
        self.filter_btn.blockSignals(False)
        self.filter_type_changed.emit(self.slot_id, self.filter_btn.get_value())
        
        # Env source
        es = state.get("env_source", 0)
        self.env_btn.blockSignals(True)
        self.env_btn.set_index(es)
        self.env_btn.blockSignals(False)
        self.env_source = es
        self.update_env_style()
        self.env_source_changed.emit(self.slot_id, self.env_source)
        self._update_retrig_param_state()
        
        # Clock rate
        cr = state.get("clock_rate", 4)
        self.rate_btn.blockSignals(True)
        self.rate_btn.set_index(cr)
        self.rate_btn.blockSignals(False)
        self.clock_rate_changed.emit(self.slot_id, self.rate_btn.get_value())
        
        # MIDI channel
        mc = state.get("midi_channel", 0)
        self.midi_channel = mc
        self.midi_btn.blockSignals(True)
        self.midi_btn.set_index(mc)
        self.midi_btn.blockSignals(False)
        self.midi_btn.setStyleSheet(midi_channel_style(mc > 0))
        self.midi_channel_changed.emit(self.slot_id, self.midi_channel)

        # Transpose
        tr = state.get("transpose", 2)  # Default to middle (0 semitones)
        self.transpose_btn.blockSignals(True)
        self.transpose_btn.set_index(tr)
        self.transpose_btn.blockSignals(False)
        self.transpose = TRANSPOSE_SEMITONES[tr]
        self.transpose_changed.emit(self.slot_id, self.transpose)

        # Portamento restoration
        port = state.get("portamento", 0.0)
        self.portamento = port
        self.portamento_knob.blockSignals(True)
        self.portamento_knob.setValue(port)
        self.portamento_knob.blockSignals(False)
        self.portamento_changed.emit(self.slot_id, self.portamento)

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
        self.transpose_btn.setEnabled(enabled)
        self.portamento_knob.setEnabled(enabled)
        self.env_btn.setEnabled(enabled)
        self.update_env_style()
        self.update_style()
        
        self.update_custom_params(gen_type)
        self.scope.set_waveform(gen_type)
    
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
    
    # =========================================================================
    # Style Updates
    # =========================================================================
    
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
            # Green accent when generator loaded (like modulators)
            border_color = COLORS.get('accent_generator', '#00ff66')
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
    
    # =========================================================================
    # Event Handlers
    # =========================================================================
    
    def on_filter_changed(self, filter_type):
        """Handle filter button change."""
        logger.gen(self.slot_id, f"filter: {filter_type}")
        self.filter_type_changed.emit(self.slot_id, filter_type)
    
    def on_generator_type_changed(self, gen_type):
        """Handle generator type change from CycleButton."""
        self.generator_type = gen_type
        logger.gen(self.slot_id, f"type: {gen_type}")
        self.generator_changed.emit(self.slot_id, gen_type)
        self.update_custom_params(gen_type)
        self.update_env_style()
        self.update_style()
        self.scope.set_waveform(gen_type)
        
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

    def on_transpose_changed(self, transpose_str):
        """Handle transpose button change."""
        index = self.transpose_btn.index
        self.transpose = TRANSPOSE_SEMITONES[index]
        logger.gen(self.slot_id, f"transpose: {transpose_str} ({self.transpose} semitones)")
        self.transpose_changed.emit(self.slot_id, self.transpose)

        # Re-send frequency so transpose takes effect immediately
        if 'frequency' in self.sliders:
            freq_slider = self.sliders['frequency']
            freq_normalized = freq_slider.value() / 1000.0
            freq_param = next((p for p in GENERATOR_PARAMS if p['key'] == 'frequency'), None)
            if freq_param:
                freq_real = map_value(freq_normalized, freq_param)
                self.parameter_changed.emit(self.slot_id, 'frequency', freq_real)

    def on_portamento_changed(self, value):
        """Handle portamento knob change."""
        self.portamento = value
        logger.gen(self.slot_id, f"portamento: {value:.3f}")
        self.portamento_changed.emit(self.slot_id, self.portamento)
        
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
    
    def toggle_mute(self, _=None):
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
