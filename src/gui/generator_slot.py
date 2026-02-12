"""
Generator Slot v3 - Flat absolute positioning with full functionality
Styled like ModulatorSlot - green accent border when loaded
"""
from PyQt5.QtWidgets import QWidget, QLabel, QFrame, QSizePolicy
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QEvent
from PyQt5.QtGui import QFont

from .widgets import DragSlider, CycleButton, MiniKnob
from .theme import (COLORS, FONT_FAMILY, MONO_FONT, FONT_SIZES, button_style,
                    mute_button_style, gate_indicator_style, midi_channel_style)
from .synthesis_icon import SynthesisIcon

from src.config import (
    GENERATOR_PARAMS, MAX_CUSTOM_PARAMS, GENERATOR_CYCLE,
    get_generator_custom_params, get_generator_pitch_target,
    get_generator_midi_retrig, get_generator_retrig_param_index,
    CLOCK_RATES, FILTER_TYPES, ENV_SOURCES, ENV_SOURCE_INDEX,
    ANALOG_TYPES, ANALOG_TYPE_INDEX, ANALOG_UI_LABELS,
    TRANSPOSE_SEMITONES, map_value, format_value, get_generator_synthesis_category
)
from src.utils.logger import logger

# P0.2: Module-scope imports (was inline in get_state/apply_state)
from src.gui.arp_engine import ArpPattern
from src.model.sequencer import StepType, PlayMode, MotionMode, SeqStep
from src.presets.preset_schema import SlotState




# =============================================================================
# LAYOUT - All positions in one place
# =============================================================================
SLOT_LAYOUT = {
    'slot_width': 180,
    'slot_height': 326,

    # Header
    'gen_label_x': 5, 'gen_label_y': 5,
    'gen_label_w': 40, 'gen_label_h': 20,
    'selector_x': 36, 'selector_y': 2,  # R1.1: adjusted x for wider button
    'selector_w': 140, 'selector_h': 22,  # R1.1: increased from 110 to 140px

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
    # Analog stage cycle button at y=56
    'btn_analog_x': 134, 'btn_analog_y': 56,
    'btn_analog_w': 34, 'btn_analog_h': 18,
    'btn_env_y': 76,
    'btn_rate_y': 100,
    'btn_trans_y': 124,
    'btn_midi_y': 148,
    'btn_mute_y': 172,

    # Gate & Portamento
    'gate_x': 134, 'gate_y': 196, 'gate_w': 34, 'gate_h': 14,
    'port_x': 142, 'port_y': 212, 'port_w': 18, 'port_h': 80,
}

L = SLOT_LAYOUT


class GeneratorSlot(QWidget):
    """Generator slot with flat absolute positioning and full functionality."""

    _ANALOG_DRAG_THRESHOLD = 10  # Pixels — ignore micro-jitters below this

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
    analog_enable_changed = pyqtSignal(int, int)  # slot_id, enabled (0|1)
    analog_type_changed = pyqtSignal(int, int)  # slot_id, type_index (0-3)
    molti_load_requested = pyqtSignal(int)  # slot_id — user clicked LOAD on MOLTI-SAMP slot
    
    def __init__(self, slot_id, generator_type="Empty", parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        
        self.slot_id = slot_id
        self.setObjectName(f"gen{slot_id}_slot")
        self.generator_type = generator_type
        self.active = False
        self.clock_enabled = False  # Legacy
        self.env_source = 2  # 0=OFF, 1=CLK, 2=MIDI (default to MIDI)
        self.muted = False
        self.midi_channel = 0  # 0 = OFF, 1-16 = channels
        self.transpose = 0  # Semitones (-24 to +24)
        self.portamento = 0  # Portamento time (0-1)
        self.analog_enabled = 0  # 0=OFF, 1=ON (sticky across generator changes)
        self.analog_type = 0  # 0=CLEAN, 1=TAPE, 2=TUBE, 3=FOLD (sticky)

        # MOLTI-SAMP state
        self.molti_path = None   # Path to loaded .korgmultisample file (str)
        self.molti_name = ""     # Display name of loaded multisample
        self._molti_recent_path = None  # Set by right-click recent menu before signal

        # State sources (injected via set_state_sources after construction)
        self._arp_manager = None
        self._motion_manager = None

        self.setFixedWidth(L['slot_width'])
        self.setMinimumHeight(L['slot_height'])
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        
        # Gate indicator flash timer
        self.gate_timer = QTimer()
        self.gate_timer.timeout.connect(self._gate_off)
        self.gate_timer.setSingleShot(True)

        # Analog hold-bypass: press-and-hold for momentary A/B bypass
        self._analog_hold_timer = QTimer()
        self._analog_hold_timer.setSingleShot(True)
        self._analog_hold_timer.timeout.connect(self._analog_hold_activate)
        self._analog_hold_active = False  # True while hold-bypass is engaged
        self._analog_press_pos = None     # Mouse position at press (for drag threshold)

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
        self.type_btn.section_boundary = "────"  # Wrap within pack sections (core stays in core)
        self.type_btn.setGeometry(L['selector_x'], L['selector_y'],
                                   L['selector_w'], L['selector_h'])
        self.type_btn.value_changed.connect(self.on_generator_type_changed)
        self.type_btn.setFont(QFont(MONO_FONT, FONT_SIZES["small"]))
        self.type_btn.setStyleSheet(button_style("submenu"))
        self.type_btn.setToolTip(self.generator_type)  # R1.1: tooltip shows full name

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
            slider.setObjectName(f"gen_{self.slot_id}_custom{i}")
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
            slider.setObjectName(f"gen_{self.slot_id}_{key}")
            
            # Find param config and set it
            param_config = next((p for p in GENERATOR_PARAMS if p['key'] == key), None)
            if param_config:
                slider.set_param_config(param_config, format_value)
                slider.valueChanged.connect(
                    lambda v, k=key, pc=param_config: self.on_param_changed(k, v / 1000.0, pc)
                )

            slider.setEnabled(False)  # Disabled until generator loaded
            self.sliders[key] = slider
        
        # ----- BUTTONS -----
        btn_x, btn_w, btn_h = L['btn_x'], L['btn_w'], L['btn_h']
        
        self.filter_btn = CycleButton(FILTER_TYPES, parent=self)
        self.filter_btn.setGeometry(btn_x, L['btn_filter_y'], btn_w, btn_h)
        self.filter_btn.value_changed.connect(self.on_filter_changed)
        self.filter_btn.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        self.filter_btn.setStyleSheet(button_style('submenu'))
        self.filter_btn.setEnabled(False)

        # ----- ANALOG STAGE (single cycle: OFF → CLEAN → TAPE → TUBE → FOLD) -----
        # OFF is a UI macro (enable=0), CLEAN/TAPE/TUBE/FOLD map to type 0/1/2/3
        self.analog_btn = CycleButton(ANALOG_UI_LABELS, parent=self)
        self.analog_btn.setGeometry(
            L['btn_analog_x'], L['btn_analog_y'],
            L['btn_analog_w'], L['btn_analog_h'])
        self.analog_btn.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        self.analog_btn.setStyleSheet(button_style('disabled'))
        self.analog_btn.value_changed.connect(self._on_analog_btn_changed)
        self.analog_btn.setToolTip("Analog: OFF/CLEAN/TAPE/TUBE/FOLD (hold for bypass)")
        self.analog_btn.setEnabled(False)
        self.analog_btn.installEventFilter(self)

        self.env_btn = CycleButton(ENV_SOURCES, parent=self)
        self.env_btn.setGeometry(btn_x, L['btn_env_y'], btn_w, btn_h)
        self.env_btn.value_changed.connect(self.on_env_source_changed)
        self.env_btn.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        self.env_btn.setEnabled(False)
        
        self.rate_btn = CycleButton(CLOCK_RATES, parent=self)
        self.rate_btn.setGeometry(btn_x, L['btn_rate_y'], btn_w, btn_h)
        self.rate_btn.value_changed.connect(self.on_rate_changed)
        self.rate_btn.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        self.rate_btn.set_index(4)  # Default to 1/4
        self.rate_btn.setEnabled(False)

        self.transpose_btn = CycleButton([str(s) for s in TRANSPOSE_SEMITONES], parent=self)
        self.transpose_btn.setGeometry(btn_x, L['btn_trans_y'], btn_w, btn_h)
        self.transpose_btn.value_changed.connect(self.on_transpose_changed)
        self.transpose_btn.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        self.transpose_btn.setStyleSheet(button_style('submenu'))
        self.transpose_btn.set_index(2)  # Default to 0 semitones
        self.transpose_btn.setEnabled(False)

        midi_values = ['OFF'] + [str(i) for i in range(1, 17)]
        self.midi_btn = CycleButton(midi_values, parent=self)
        self.midi_btn.setGeometry(btn_x, L['btn_midi_y'], btn_w, btn_h)
        self.midi_btn.value_changed.connect(self.on_midi_channel_changed)
        self.midi_btn.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        self.midi_btn.setStyleSheet(midi_channel_style(False))
        self.midi_btn.setEnabled(False)
        
        self.mute_btn = CycleButton(['M', 'M'], parent=self)
        self.mute_btn.setGeometry(btn_x, L['btn_mute_y'], btn_w, btn_h)
        self.mute_btn.value_changed.connect(self.toggle_mute)
        self.mute_btn.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        self.mute_btn.setStyleSheet(mute_button_style(False))
        self.mute_btn.setEnabled(False)
        
        # ----- GATE INDICATOR -----
        self.gate_led = QLabel(self)
        self.gate_led.setGeometry(L['gate_x'], L['gate_y'], L['gate_w'], L['gate_h'])
        self.gate_led.setStyleSheet(gate_indicator_style(False))
        self.gate_led.setEnabled(False)

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
        self.portamento_knob.setEnabled(False)
        
        # ----- SCOPE -----
        self.scope = SynthesisIcon(self)
        self.scope.setGeometry(5, L['slot_height'] - 55, 120, 50)

        # ----- MOLTI-SAMP LOAD BUTTON + NAME LABEL -----
        from PyQt5.QtWidgets import QPushButton
        self.molti_load_btn = QPushButton("LOAD", self)
        self.molti_load_btn.setGeometry(5, L['slot_height'] - 55, 50, 22)
        self.molti_load_btn.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        self.molti_load_btn.setStyleSheet(button_style('submenu'))
        self.molti_load_btn.setToolTip("Load .korgmultisample file (right-click for recent)")
        self.molti_load_btn.clicked.connect(self._on_molti_load_clicked)
        self.molti_load_btn.setContextMenuPolicy(Qt.CustomContextMenu)
        self.molti_load_btn.customContextMenuRequested.connect(self._on_molti_load_context)
        self.molti_load_btn.hide()

        self.molti_name_label = QLabel("", self)
        self.molti_name_label.setGeometry(5, L['slot_height'] - 30, 120, 16)
        self.molti_name_label.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        self.molti_name_label.setStyleSheet(f"color: {COLORS['text_dim']};")
        self.molti_name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.molti_name_label.hide()

        # Initial env style
        self.update_env_style()
    
    # =========================================================================
    # State Management
    # =========================================================================
    
    def set_state_sources(self, arp_manager=None, motion_manager=None):
        """Inject state sources for canonical export (Phase 2 ownership shift)."""
        self._arp_manager = arp_manager
        self._motion_manager = motion_manager

    def get_state(self) -> dict:
        """Get current slot state for preset save — canonical export.

        Returns a dict matching SlotState.to_dict() schema exactly.
        The controller must not patch or fix up this output.
        """
        params = {}
        for key, slider in self.sliders.items():
            params[key] = slider.value() / 1000.0

        for i in range(MAX_CUSTOM_PARAMS):
            params[f"custom_{i}"] = self.custom_sliders[i].value() / 1000.0

        d = {
            "generator": self.generator_type if self.generator_type != "Empty" else None,
            "params": params,
            "filter_type": self.filter_btn.index,
            "env_source": self.env_source,
            "clock_rate": self.rate_btn.index,
            "midi_channel": self.midi_channel,
            "transpose": self.transpose_btn.index,
            "portamento": self.portamento,
            "analog_enabled": self.analog_enabled,
            "analog_type": self.analog_type,
            "molti_path": self.molti_path,
        }

        # ARP + Euclidean + RST state
        slot_idx = self.slot_id - 1
        if self._arp_manager is not None:
            engine = self._arp_manager.get_engine(slot_idx)
            arp = engine.get_settings()
            d["arp_enabled"] = arp.enabled
            d["arp_rate"] = arp.rate_index
            d["arp_pattern"] = list(type(arp.pattern)).index(arp.pattern)
            d["arp_octaves"] = arp.octaves
            d["arp_hold"] = arp.hold
            d["euclid_enabled"] = arp.euclid_enabled
            d["euclid_n"] = arp.euclid_n
            d["euclid_k"] = arp.euclid_k
            d["euclid_rot"] = arp.euclid_rot
            rst_idx = engine.runtime.rst_fabric_idx
            d["rst_rate"] = rst_idx if rst_idx is not None else 0
            # Step engine: expanded ARP note list
            d["arp_notes"] = list(engine._get_expanded_list())

        # Step mode (SC step engine active for this slot)
        if self._motion_manager is not None:
            mode = self._motion_manager.get_mode(slot_idx)
            d["step_mode"] = mode in (MotionMode.ARP, MotionMode.SEQ)

        # SEQ state
        if self._motion_manager is not None:
            mm = self._motion_manager
            seq_engine = mm.get_seq_engine(slot_idx)
            if seq_engine is not None:
                seq = seq_engine.get_settings()
                step_types = list(StepType)
                play_modes = list(PlayMode)
                d["seq_enabled"] = mm.get_mode(slot_idx) == MotionMode.SEQ
                d["seq_rate"] = seq_engine.rate_index
                d["seq_length"] = seq.length
                d["seq_play_mode"] = play_modes.index(seq.play_mode) if seq.play_mode in play_modes else 0
                d["seq_steps"] = [
                    {
                        "step_type": step_types.index(s.step_type) if s.step_type in step_types else 1,
                        "note": s.note,
                        "velocity": s.velocity,
                    }
                    for s in seq.steps
                ]

        return d

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

        # Analog stage restoration (sticky)
        ae = state.get("analog_enabled", 0)
        at = state.get("analog_type", 0)
        self.analog_enabled = ae
        self.analog_type = at
        # Map to UI: OFF=0, CLEAN=1, TAPE=2, TUBE=3, FOLD=4
        # SC type 0-3 maps to UI index 1-4 when enabled, 0 when disabled
        ui_idx = 0 if not ae else (at + 1)
        self.analog_btn.blockSignals(True)
        self.analog_btn.set_index(ui_idx)
        self.analog_btn.blockSignals(False)
        self.analog_btn.setStyleSheet(
            button_style('enabled') if ae else button_style('disabled'))
        self.analog_type_changed.emit(self.slot_id, self.analog_type)
        self.analog_enable_changed.emit(self.slot_id, self.analog_enabled)

        # MOLTI-SAMP path (restored from preset; actual loading is done by controller)
        mp = state.get("molti_path")
        self.molti_path = mp if mp else None

    def apply_state(self, slot_state: SlotState):
        """Apply full slot state from preset load — canonical import.

        Accepts a typed SlotState (not raw dict) to enforce the
        deserialize -> validate -> apply chain.
        Sets UI controls AND pushes feature state (ARP/Euclid/RST/SEQ)
        into injected managers. The controller must not do this separately.
        """
        # UI controls (generator, params, filter, env, clock, midi, etc.)
        self.set_state(slot_state.to_dict())

        slot_idx = self.slot_id - 1

        # Mode-symmetric: explicitly clear mode before applying features.
        # Prevents leftover ARP/SEQ mode from previous preset.
        if self._motion_manager is not None:
            self._motion_manager.set_mode(slot_idx, MotionMode.OFF)

        # ARP + Euclidean + RST state
        if self._arp_manager is not None:
            self._apply_arp_state(slot_idx, slot_state)

        # SEQ state
        if self._motion_manager is not None:
            self._apply_seq_state(slot_idx, slot_state)

    def _apply_arp_state(self, slot_idx: int, slot_state: SlotState):
        """Push ARP + Euclidean + RST state into the arp engine."""
        engine = self._arp_manager.get_engine(slot_idx)
        patterns = list(ArpPattern)
        pattern_idx = slot_state.arp_pattern
        pattern = patterns[pattern_idx] if 0 <= pattern_idx < len(patterns) else ArpPattern.UP
        engine.set_rate(slot_state.arp_rate)
        engine.set_pattern(pattern)
        engine.set_octaves(slot_state.arp_octaves)
        engine.toggle_hold(slot_state.arp_hold)
        engine.toggle_arp(slot_state.arp_enabled)
        engine.set_euclid(
            slot_state.euclid_enabled,
            slot_state.euclid_n,
            slot_state.euclid_k,
            slot_state.euclid_rot,
        )
        rst_rate = slot_state.rst_rate
        engine.runtime.rst_fabric_idx = rst_rate if rst_rate >= 4 else None
        # arp_notes: restored from preset for state tracking;
        # live notes are pushed to SC step engine by MotionManager callback
        _ = slot_state.arp_notes  # read to satisfy apply/export symmetry
        if self._motion_manager is not None and slot_state.arp_enabled:
            self._motion_manager.set_mode(slot_idx, MotionMode.ARP)

    def _apply_seq_state(self, slot_idx: int, slot_state: SlotState):
        """Push SEQ state into the seq engine, resetting stale steps first."""
        mm = self._motion_manager
        seq_engine = mm.get_seq_engine(slot_idx)
        if seq_engine is None:
            return

        step_types = list(StepType)
        play_modes = list(PlayMode)
        seq_engine._rate_index = max(0, min(slot_state.seq_rate, 6))
        seq_engine.settings.length = max(1, min(slot_state.seq_length, 16))
        pm_idx = slot_state.seq_play_mode
        seq_engine.settings.play_mode = play_modes[pm_idx] if 0 <= pm_idx < len(play_modes) else PlayMode.FORWARD

        # P0.3: Reset ALL 16 steps to REST defaults before applying.
        # Prevents stale tail when loading a preset with fewer steps.
        for j in range(16):
            seq_engine.settings.steps[j] = SeqStep()

        # Apply provided steps over the clean slate
        for j, step_dict in enumerate(slot_state.seq_steps[:16]):
            if isinstance(step_dict, dict):
                st_idx = step_dict.get("step_type", 1)
                st = step_types[st_idx] if 0 <= st_idx < len(step_types) else StepType.REST
                seq_engine.settings.steps[j] = SeqStep(
                    step_type=st,
                    note=step_dict.get("note", 60),
                    velocity=step_dict.get("velocity", 100),
                )
        seq_engine.steps_version += 1

        # step_mode: SC step engine state; restored via set_mode handover
        _ = slot_state.step_mode  # read to satisfy apply/export symmetry
        if slot_state.seq_enabled:
            mm.set_mode(slot_idx, MotionMode.SEQ)

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
        self.analog_btn.setEnabled(enabled)
        # Re-emit analog state (sticky across generator changes)
        if enabled:
            self.analog_type_changed.emit(self.slot_id, self.analog_type)
            self.analog_enable_changed.emit(self.slot_id, self.analog_enabled)
        self.transpose_btn.setEnabled(enabled)
        self.portamento_knob.setEnabled(enabled)
        self.env_btn.setEnabled(enabled)
        self.update_env_style()
        self.update_style()
        
        self.update_custom_params(gen_type)
        self.scope.set_category(get_generator_synthesis_category(gen_type))

        # MOLTI-SAMP: show/hide LOAD button and name label
        is_molti = (gen_type == "MOLTI-SAMP")
        self.molti_load_btn.setVisible(is_molti and enabled)
        self.molti_name_label.setVisible(is_molti and enabled)
        self.scope.setVisible(not is_molti)
        if not is_molti:
            self.set_molti_unloaded()

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
    
    def eventFilter(self, obj, event):
        """Intercept analog button press/release for momentary hold-bypass.

        State machine:
          Press  → record position, start 300ms timer
          Move   → cancel timer only if manhattan drag exceeds 10px
          Timer  → activate bypass (enable=0, warning style)
          Release → if bypass active: restore enable=1, consume event
                    else: let CycleButton handle the click normally
          Leave  → if bypass active: restore (prevents stuck bypass)
        """
        if obj is self.analog_btn and self.analog_enabled == 1:
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self._analog_press_pos = event.globalPos()
                self._analog_hold_timer.start(300)
            elif event.type() == QEvent.MouseMove:
                # Only process drag when left button is held
                if not (event.buttons() & Qt.LeftButton):
                    return super().eventFilter(obj, event)
                # Only cancel hold if drag exceeds threshold (ignore touchpad jitter)
                if self._analog_press_pos is not None and not self._analog_hold_active:
                    delta = event.globalPos() - self._analog_press_pos
                    if (abs(delta.x()) + abs(delta.y())) > self._ANALOG_DRAG_THRESHOLD:
                        self._analog_hold_timer.stop()
                        self._analog_press_pos = None
            elif event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                self._analog_hold_timer.stop()
                self._analog_press_pos = None
                if self._analog_hold_active:
                    # Release: restore enable and consume the event (no cycle)
                    self._analog_hold_active = False
                    self.analog_enable_changed.emit(self.slot_id, 1)
                    self.analog_btn.setStyleSheet(button_style('enabled'))
                    logger.gen(self.slot_id, "analog: hold-bypass released")
                    return True  # Consume — don't let CycleButton cycle
            elif event.type() == QEvent.Leave:
                # User left widget during hold — restore to prevent stuck bypass
                self._analog_hold_timer.stop()
                self._analog_press_pos = None
                if self._analog_hold_active:
                    self._analog_hold_active = False
                    self.analog_enable_changed.emit(self.slot_id, 1)
                    self.analog_btn.setStyleSheet(button_style('enabled'))
                    logger.gen(self.slot_id, "analog: hold-bypass released (leave)")
                    return True
        return super().eventFilter(obj, event)

    def _analog_hold_activate(self):
        """Activate momentary bypass after hold threshold."""
        if self.analog_enabled == 1:
            self._analog_hold_active = True
            self.analog_enable_changed.emit(self.slot_id, 0)
            self.analog_btn.setStyleSheet(button_style('warning'))
            logger.gen(self.slot_id, "analog: hold-bypass engaged")

    def _on_analog_btn_changed(self, ui_label):
        """Dual dispatch: single button drives both enable and type buses.
        OFF = enable=0 (type unchanged). CLEAN/TAPE/TUBE/FOLD = enable=1, type=0/1/2/3."""
        if ui_label == "OFF":
            self.analog_enabled = 0
            self.analog_btn.setStyleSheet(button_style('disabled'))
            logger.gen(self.slot_id, "analog: OFF (bypass)")
            self.analog_enable_changed.emit(self.slot_id, 0)
        else:
            self.analog_enabled = 1
            self.analog_type = ANALOG_TYPE_INDEX[ui_label]
            self.analog_btn.setStyleSheet(button_style('enabled'))
            logger.gen(self.slot_id, f"analog: {ui_label}")
            # Set type BEFORE enabling to prevent audible blips
            self.analog_type_changed.emit(self.slot_id, self.analog_type)
            self.analog_enable_changed.emit(self.slot_id, 1)

    def _on_molti_load_clicked(self):
        """Handle LOAD button click — request multisample load."""
        self.molti_load_requested.emit(self.slot_id)

    def _on_molti_load_context(self, pos):
        """Handle right-click on LOAD button — show recent files menu."""
        from src.config.molti_recent import get_recent_files
        from PyQt5.QtWidgets import QMenu, QAction
        recent = get_recent_files()
        if not recent:
            return
        menu = QMenu(self)
        for path_str in recent:
            from pathlib import Path
            name = Path(path_str).stem
            action = menu.addAction(name)
            action.setData(path_str)
        action = menu.exec_(self.molti_load_btn.mapToGlobal(pos))
        if action and action.data():
            self._molti_recent_path = action.data()
            self.molti_load_requested.emit(self.slot_id)

    def set_molti_loaded(self, name: str, path: str):
        """Update UI after multisample loaded."""
        self.molti_name = name
        self.molti_path = path
        display = name if len(name) <= 16 else name[:14] + ".."
        self.molti_name_label.setText(display)
        self.molti_name_label.setToolTip(name)
        self.molti_name_label.setStyleSheet(f"color: {COLORS['enabled_text']};")

    def set_molti_unloaded(self):
        """Reset MOLTI-SAMP UI state."""
        self.molti_name = ""
        self.molti_path = None
        self._molti_recent_path = None
        self.molti_name_label.setText("")
        self.molti_name_label.setStyleSheet(f"color: {COLORS['text_dim']};")

    def on_filter_changed(self, filter_type):
        """Handle filter button change."""
        logger.gen(self.slot_id, f"filter: {filter_type}")
        self.filter_type_changed.emit(self.slot_id, filter_type)
    
    def on_generator_type_changed(self, gen_type):
        """Handle generator type change from CycleButton."""
        self.generator_type = gen_type
        self.type_btn.setToolTip(gen_type)  # R1.1: update tooltip with full name
        logger.gen(self.slot_id, f"type: {gen_type}")
        self.generator_changed.emit(self.slot_id, gen_type)
        self.update_custom_params(gen_type)
        self.update_env_style()
        self.update_style()
        self.scope.set_category(get_generator_synthesis_category(gen_type))

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

    def get_param_widget(self, param: str):
        """
        Return slider widget for param (for boid pulse visualization).

        Args:
            param: 'frequency', 'cutoff', 'resonance', 'attack', 'decay',
                   or 'custom0'-'custom4'

        Returns:
            Widget with set_boid_glow() method, or None
        """
        # Core params
        if param in self.sliders:
            return self.sliders[param]

        # Custom params (custom0, custom1, etc.)
        if param.startswith('custom'):
            try:
                idx = int(param.replace('custom', ''))
                if 0 <= idx < len(self.custom_sliders):
                    return self.custom_sliders[idx]
            except ValueError:
                pass

        return None
