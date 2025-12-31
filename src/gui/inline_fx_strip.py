"""
Inline FX Strip Component
Compact horizontal FX controls for bottom banner
Heat | Echo | Reverb | Filter | [Full Window]
"""

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame, QPushButton, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from .theme import COLORS, MONO_FONT, FONT_FAMILY, FONT_SIZES
from .widgets import MiniKnob, CycleButton
from src.config import OSC_PATHS, CLOCK_RATES, CLOCK_DEFAULT_INDEX

# Filter sync: FREE + standard CLOCK_RATES (same as envelope)
# Order: FREE, /32, /16, /12, /8, /4, /2, CLK, x2, x4, x8, x12, x16, x32
FILTER_SYNC_MODES = ["FREE"] + CLOCK_RATES
FILTER_SYNC_CLK_INDEX = CLOCK_DEFAULT_INDEX + 1  # CLK index (offset by FREE)

class FXModule(QFrame):
    """Base class for inline FX module."""
    
    # Turbo states
    TURBO_OFF = 0
    TURBO_T1 = 1
    TURBO_T2 = 2
    
    def __init__(self, name, has_bypass=False, has_turbo=True, parent=None):
        super().__init__(parent)
        self.name = name
        self.setObjectName(f"{name}Module")
        self.has_bypass = has_bypass
        self.has_turbo = has_turbo
        self.bypassed = True if has_bypass else False
        self.turbo_state = self.TURBO_OFF
        self.osc_bridge = None
        self.knobs = {}
        self.setup_base_ui()
        
    def setup_base_ui(self):
        """Create base module frame."""
        self.setStyleSheet(f"""
            FXModule {{
                background-color: {COLORS['background']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
            }}
        """)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 6, 8, 6)
        self.main_layout.setSpacing(4)
        
        # Title row (clickable)
        title_row = QHBoxLayout()
        title_row.setSpacing(6)
        
        self.title_label = QLabel(self.name)
        self.title_label.setFont(QFont(FONT_FAMILY, FONT_SIZES['small'], QFont.Bold))
        self.title_label.setStyleSheet(f"color: {COLORS['accent_effect']};")
        title_row.addWidget(self.title_label)
        
        title_row.addStretch()
        
        # Turbo button (if applicable)
        if self.has_turbo:
            self.turbo_btn = QPushButton("TRB")
            self.turbo_btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['micro'], QFont.Bold))
            self.turbo_btn.setFixedSize(25, 16)
            self.turbo_btn.clicked.connect(self._cycle_turbo)
            self._update_turbo_style()
            title_row.addWidget(self.turbo_btn)
        
        # Bypass button (if applicable)
        if self.has_bypass:
            self.bypass_btn = QPushButton("BYP")
            self.bypass_btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['tiny']))
            self.bypass_btn.setFixedSize(32, 18)
            self.bypass_btn.clicked.connect(self._toggle_bypass)
            self._update_bypass_style()
            title_row.addWidget(self.bypass_btn)
        
        self.main_layout.addLayout(title_row)
        
        # Knobs row - give it stretch to expand
        self.knobs_layout = QHBoxLayout()
        self.knobs_layout.setSpacing(10)
        self.main_layout.addLayout(self.knobs_layout, stretch=1)
        
        # Bottom row (labels/status)
        self.bottom_layout = QHBoxLayout()
        self.bottom_layout.setSpacing(6)
        self.main_layout.addLayout(self.bottom_layout)
        
    def add_knob(self, name, default=100, tooltip=""):
        """Add a labeled knob (larger than MiniKnob for usability)."""
        container = QVBoxLayout()
        container.setSpacing(2)
        container.setContentsMargins(0, 0, 0, 0)
        
        # Create larger knob
        knob = MiniKnob()
        knob.setObjectName(f"fx_{self.name.lower()}_{name.lower()}")
        knob.setFixedSize(22, 22)  # Larger than default 18x18
        knob.setValue(default)
        knob.setToolTip(tooltip or f"{name} (double-click reset)")
        container.addWidget(knob, alignment=Qt.AlignCenter)
        
        label = QLabel(name)
        label.setFont(QFont(MONO_FONT, FONT_SIZES['tiny']))
        label.setStyleSheet(f"color: {COLORS['text_dim']};")
        label.setAlignment(Qt.AlignCenter)
        #container.addWidget(label, alignment=Qt.AlignCenter)
        container.addWidget(label)
        
        self.knobs_layout.addLayout(container)
        self.knobs[name] = knob
        return knob
        
    def _toggle_bypass(self):
        """Toggle bypass state."""
        self.bypassed = not self.bypassed
        self._update_bypass_style()
        self._on_bypass_changed()
    
    def _cycle_turbo(self):
        """Cycle through turbo states: OFF → T1 → T2 → OFF."""
        self.turbo_state = (self.turbo_state + 1) % 3
        self._update_turbo_style()
        self._apply_turbo()
    
    def _update_turbo_style(self):
        """Update turbo button appearance."""
        if not self.has_turbo:
            return
            
        if self.turbo_state == self.TURBO_OFF:
            self.turbo_btn.setText("INI")
            self.turbo_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['background_dark']};
                    color: {COLORS['text']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 2px;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    border-color: {COLORS['text_dim']};
                }}
            """)
        elif self.turbo_state == self.TURBO_T1:
            self.turbo_btn.setText("T1")
            self.turbo_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['turbo_t1']};
                    color: {COLORS['background_dark']};
                    border: 1px solid {COLORS['turbo_t1']};
                    border-radius: 2px;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['turbo_t1']};
                }}
            """)
        else:  # T2
            self.turbo_btn.setText("T2")
            self.turbo_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['turbo_t2']};
                    color: {COLORS['text']};
                    border: 1px solid {COLORS['turbo_t2']};
                    border-radius: 2px;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['turbo_t2']};
                }}
            """)
    
    def _apply_turbo(self):
        """Override in subclass to apply turbo presets."""
        pass
        
    def _update_bypass_style(self):
        """Update bypass button appearance."""
        if not self.has_bypass:
            return
            
        if self.bypassed:
            # BYPASSED - red/warning
            self.bypass_btn.setText("BYP")
            self.bypass_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['warning']};
                    color: {COLORS['warning_text']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 2px;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['warning_hover']};
                }}
            """)
        else:
            # ACTIVE - green
            self.bypass_btn.setText("ON")
            self.bypass_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['enabled']};
                    color: {COLORS['enabled_text']};
                    border: 1px solid {COLORS['border_active']};
                    border-radius: 2px;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['enabled_hover']};
                }}
            """)
            
    def _on_bypass_changed(self):
        """Override in subclass to handle bypass."""
        pass
        
    def set_osc_bridge(self, osc_bridge):
        """Set OSC bridge for sending messages."""
        self.osc_bridge = osc_bridge
        
    def _send_osc(self, path, value):
        """Send OSC message if connected."""
        if self.osc_bridge and self.osc_bridge.client:
            self.osc_bridge.client.send_message(path, [value])
    
    def sync_state(self):
        """Override in subclass to sync all state to SC on reconnect."""
        pass


class HeatModule(FXModule):
    """Heat saturation module."""
    
    CIRCUITS = ["CLEAN", "TAPE", "TUBE", "CRUNCH"]
    
    def __init__(self, parent=None):
        super().__init__("HEAT", has_bypass=True, has_turbo=True, parent=parent)
        self.circuit_index = 0
        self.setup_controls()
        
    def setup_controls(self):
        """Add Heat-specific controls."""
        # Knobs - INI state: 50% mix
        self.drive_knob = self.add_knob("DRV", 0, "Drive amount")
        self.mix_knob = self.add_knob("MIX", 100, "Dry/Wet mix")
        
        # Circuit label (clickable to cycle)
        self.circuit_label = QLabel(self.CIRCUITS[0])
        self.circuit_label.setFont(QFont(MONO_FONT, FONT_SIZES['small']))
        self.circuit_label.setStyleSheet(f"color: {COLORS['text']};")
        self.circuit_label.setAlignment(Qt.AlignCenter)
        self.circuit_label.setCursor(Qt.PointingHandCursor)
        self.circuit_label.mousePressEvent = self._cycle_circuit
        self.bottom_layout.addWidget(self.circuit_label)
        
        # Connect knobs
        self.drive_knob.valueChanged.connect(
            lambda v: self._send_osc(OSC_PATHS['heat_drive'], v / 200.0))
        self.mix_knob.valueChanged.connect(
            lambda v: self._send_osc(OSC_PATHS['heat_mix'], v / 200.0))
            
    def _cycle_circuit(self, event):
        """Cycle through circuit types."""
        self.circuit_index = (self.circuit_index + 1) % len(self.CIRCUITS)
        self.circuit_label.setText(self.CIRCUITS[self.circuit_index])
        self._send_osc(OSC_PATHS['heat_circuit'], self.circuit_index)
        
    def _on_bypass_changed(self):
        """Send bypass state."""
        self._send_osc(OSC_PATHS['heat_bypass'], 1 if self.bypassed else 0)
    
    def _apply_turbo(self):
        """Apply turbo presets for Heat. 50% → 75% → 100%."""
        if self.turbo_state == self.TURBO_OFF:
            # INI: Clean, subtle - 50%
            self.circuit_index = 0
            self.circuit_label.setText(self.CIRCUITS[0])
            self._send_osc(OSC_PATHS['heat_circuit'], 0)
            self.drive_knob.setValue(50)
            self.mix_knob.setValue(100)  # 50%
        elif self.turbo_state == self.TURBO_T1:
            # T1: Tape warmth - 75%
            self.circuit_index = 1  # TAPE
            self.circuit_label.setText(self.CIRCUITS[1])
            self._send_osc(OSC_PATHS['heat_circuit'], 1)
            self.drive_knob.setValue(100)
            self.mix_knob.setValue(150)  # 75%
        else:  # T2
            # T2: Full crunch - 100%
            self.circuit_index = 3  # CRUNCH
            self.circuit_label.setText(self.CIRCUITS[3])
            self._send_osc(OSC_PATHS['heat_circuit'], 3)
            self.drive_knob.setValue(160)
            self.mix_knob.setValue(200)  # 100%
    
    def sync_state(self):
        """Sync all Heat state to SC on reconnect."""
        self._send_osc(OSC_PATHS['heat_bypass'], 1 if self.bypassed else 0)
        self._send_osc(OSC_PATHS['heat_circuit'], self.circuit_index)
        self._send_osc(OSC_PATHS['heat_drive'], self.drive_knob.value() / 200.0)
        self._send_osc(OSC_PATHS['heat_mix'], self.mix_knob.value() / 200.0)


class EchoModule(FXModule):
    """Tape Echo module (send effect - no bypass)."""
    
    def __init__(self, parent=None):
        super().__init__("ECHO", has_bypass=False, has_turbo=True, parent=parent)
        self.verb_send_on = False
        self._echo_tone = 0.5  # Track tone value (set via turbo)
        self.setup_controls()
        
    def setup_controls(self):
        """Add Echo-specific controls."""
        # INI state: 50% RTN, sensible time/feedback
        self.time_knob = self.add_knob("TIME", 120, "Delay time")
        self.feedback_knob = self.add_knob("FBK", 100, "Feedback amount")
        self.wow_knob = self.add_knob("WOW", 0, "Tape wobble/flutter")
        self.spring_knob = self.add_knob("SPR", 0, "Spring reverb amount")
        self.return_knob = self.add_knob("RTN", 100, "Return level")
        
        # Verb send button (fixed 50% toggle)
        self.verb_btn = QPushButton("→VB")
        self.verb_btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['micro']))
        self.verb_btn.setFixedSize(28, 16)
        self.verb_btn.setToolTip("Send echo to reverb (50%)")
        self.verb_btn.clicked.connect(self._toggle_verb_send)
        self._update_verb_btn_style()
        self.bottom_layout.addWidget(self.verb_btn)
        
        # Connect knobs
        self.time_knob.valueChanged.connect(
            lambda v: self._send_osc(OSC_PATHS['echo_time'], v / 200.0))
        self.feedback_knob.valueChanged.connect(
            lambda v: self._send_osc(OSC_PATHS['echo_feedback'], v / 200.0))
        self.wow_knob.valueChanged.connect(
            lambda v: self._send_osc(OSC_PATHS['echo_wow'], v / 200.0))
        self.spring_knob.valueChanged.connect(
            lambda v: self._send_osc(OSC_PATHS['echo_spring'], v / 200.0))
        self.return_knob.valueChanged.connect(
            lambda v: self._send_osc(OSC_PATHS['master_echo_return'], v / 200.0))
    
    def _toggle_verb_send(self):
        """Toggle verb send on/off at 50%."""
        self.verb_send_on = not self.verb_send_on
        self._update_verb_btn_style()
        self._send_osc(OSC_PATHS['echo_verb_send'], 0.5 if self.verb_send_on else 0.0)
    
    def _update_verb_btn_style(self):
        """Update verb send button appearance."""
        if self.verb_send_on:
            self.verb_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['enabled']};
                    color: {COLORS['enabled_text']};
                    border: 1px solid {COLORS['border_active']};
                    border-radius: 2px;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['enabled_hover']};
                }}
            """)
        else:
            self.verb_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['background_dark']};
                    color: {COLORS['text_dim']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 2px;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    border-color: {COLORS['text_dim']};
                }}
            """)
    
    def _apply_turbo(self):
        """Apply turbo presets for Echo. 50% → 75% → 100%."""
        if self.turbo_state == self.TURBO_OFF:
            # INI: Clean echo - 50%
            self._echo_tone = 0.5
            self._send_osc(OSC_PATHS['echo_tone'], self._echo_tone)
            self.wow_knob.setValue(0)
            self.spring_knob.setValue(0)
            self.verb_send_on = False
            self._update_verb_btn_style()
            self._send_osc(OSC_PATHS['echo_verb_send'], 0.0)
            self.time_knob.setValue(120)
            self.feedback_knob.setValue(100)
            self.return_knob.setValue(100)  # 50%
        elif self.turbo_state == self.TURBO_T1:
            # T1: Warm tape - 75%
            self._echo_tone = 0.35
            self._send_osc(OSC_PATHS['echo_tone'], self._echo_tone)
            self.wow_knob.setValue(60)
            self.spring_knob.setValue(50)
            self.verb_send_on = False
            self._update_verb_btn_style()
            self._send_osc(OSC_PATHS['echo_verb_send'], 0.0)
            self.time_knob.setValue(140)
            self.feedback_knob.setValue(130)
            self.return_knob.setValue(150)  # 75%
        else:  # T2
            # T2: Drippy madness - 100%
            self._echo_tone = 0.2
            self._send_osc(OSC_PATHS['echo_tone'], self._echo_tone)
            self.wow_knob.setValue(120)
            self.spring_knob.setValue(140)
            self.verb_send_on = True
            self._update_verb_btn_style()
            self._send_osc(OSC_PATHS['echo_verb_send'], 0.5)
            self.time_knob.setValue(160)
            self.feedback_knob.setValue(170)
            self.return_knob.setValue(200)  # 100%
    
    def sync_state(self):
        """Sync all Echo state to SC on reconnect."""
        self._send_osc(OSC_PATHS['echo_time'], self.time_knob.value() / 200.0)
        self._send_osc(OSC_PATHS['echo_feedback'], self.feedback_knob.value() / 200.0)
        self._send_osc(OSC_PATHS['echo_wow'], self.wow_knob.value() / 200.0)
        self._send_osc(OSC_PATHS['echo_spring'], self.spring_knob.value() / 200.0)
        self._send_osc(OSC_PATHS['master_echo_return'], self.return_knob.value() / 200.0)
        self._send_osc(OSC_PATHS['echo_verb_send'], 0.5 if self.verb_send_on else 0.0)
        self._send_osc(OSC_PATHS['echo_tone'], self._echo_tone)


class ReverbModule(FXModule):
    """Reverb module (send effect - no bypass)."""
    
    def __init__(self, parent=None):
        super().__init__("REVERB", has_bypass=False, has_turbo=True, parent=parent)
        self.setup_controls()
        
    def setup_controls(self):
        """Add Reverb-specific controls."""
        # INI state: Big space, controlled tail, prominent
        self.size_knob = self.add_knob("SIZ", 150, "Room size")
        self.decay_knob = self.add_knob("DEC", 130, "Decay time")
        self.tone_knob = self.add_knob("TONE", 100, "Brightness")
        self.return_knob = self.add_knob("RTN", 170, "Return level")
        
        # Connect knobs
        self.size_knob.valueChanged.connect(
            lambda v: self._send_osc(OSC_PATHS['verb_size'], v / 200.0))
        self.decay_knob.valueChanged.connect(
            lambda v: self._send_osc(OSC_PATHS['verb_decay'], v / 200.0))
        self.tone_knob.valueChanged.connect(
            lambda v: self._send_osc(OSC_PATHS['verb_tone'], v / 200.0))
        self.return_knob.valueChanged.connect(
            lambda v: self._send_osc(OSC_PATHS['master_verb_return'], v / 200.0))
    
    def _apply_turbo(self):
        """Apply turbo presets for Reverb. Scaled from INI: 75%/65%/85%."""
        if self.turbo_state == self.TURBO_OFF:
            # INI: Big hall, controlled - 75%/65%/85%
            self.size_knob.setValue(150)   # 75%
            self.decay_knob.setValue(130)  # 65%
            self.tone_knob.setValue(100)   # neutral
            self.return_knob.setValue(170) # 85%
        elif self.turbo_state == self.TURBO_T1:
            # T1: Larger, longer - scale up ~15%
            self.size_knob.setValue(180)   # 90%
            self.decay_knob.setValue(165)  # 82.5%
            self.tone_knob.setValue(80)    # slightly darker
            self.return_knob.setValue(190) # 95%
        else:  # T2
            # T2: Full send - max everything
            self.size_knob.setValue(200)   # 100%
            self.decay_knob.setValue(200)  # 100%
            self.tone_knob.setValue(130)   # shimmer bright
            self.return_knob.setValue(200) # 100%
    
    def sync_state(self):
        """Sync all Reverb state to SC on reconnect."""
        self._send_osc(OSC_PATHS['verb_size'], self.size_knob.value() / 200.0)
        self._send_osc(OSC_PATHS['verb_decay'], self.decay_knob.value() / 200.0)
        self._send_osc(OSC_PATHS['verb_tone'], self.tone_knob.value() / 200.0)
        self._send_osc(OSC_PATHS['master_verb_return'], self.return_knob.value() / 200.0)


class FilterModule(FXModule):
    """Dual Filter module."""
    
    MODES = ["LP", "BP", "HP"]
    ROUTINGS = ["SER", "PAR"]
    
    def __init__(self, parent=None):
        super().__init__("FILTER", has_bypass=True, has_turbo=True, parent=parent)
        self.routing_index = 0
        self.f1_mode_index = 0  # LP default
        self.f2_mode_index = 0  # LP default
        self.f1_prev_sync = 0   # Track previous sync index
        self.f2_prev_sync = 0
        # Track turbo-only params
        self._drive_value = 0.0
        self._harmonics_value = 0
        self.setup_controls()
    
    def _add_filter_knob(self, name, default, mode_index, tooltip):
        """Add a knob with clickable filter mode label."""
        container = QVBoxLayout()
        container.setSpacing(2)
        container.setContentsMargins(0, 0, 0, 0)
        
        knob = MiniKnob()
        knob.setObjectName(f"fx_filter_{name.lower()}")
        knob.setFixedSize(22, 22)
        knob.setValue(default)
        knob.setToolTip(tooltip)
        container.addWidget(knob, alignment=Qt.AlignCenter)
        
        # Clickable mode label (LP/BP/HP)
        mode_label = QLabel(self.MODES[mode_index])
        mode_label.setFont(QFont(MONO_FONT, FONT_SIZES['tiny']))
        mode_label.setStyleSheet(f"color: {COLORS['text']};")
        mode_label.setAlignment(Qt.AlignCenter)
        mode_label.setCursor(Qt.PointingHandCursor)
        mode_label.setFixedWidth(19)
        container.addWidget(mode_label)
        
        self.knobs_layout.addLayout(container)
        self.knobs[name] = knob
        return knob, mode_label
    
    def _create_sync_btn(self, name):
        """Create a sync CycleButton - same as envelope CLK but with FREE option."""
        btn = CycleButton(FILTER_SYNC_MODES, initial_index=0)  # Start at FREE
        btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['micro']))
        btn.setFixedSize(36, 16)
        btn.setToolTip(f"{name} sync: click for CLK, drag to change rate")
        btn.wrap = True
        self._update_sync_btn_style(btn, 0)
        return btn
    
    def _update_sync_btn_style(self, btn, index):
        """Update sync button appearance based on mode."""
        if index == 0:  # FREE
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['background_dark']};
                    color: {COLORS['text_dim']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 2px;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    border-color: {COLORS['text_dim']};
                }}
            """)
        else:  # Any clock rate
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['enabled']};
                    color: {COLORS['enabled_text']};
                    border: 1px solid {COLORS['border_active']};
                    border-radius: 2px;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['enabled_hover']};
                }}
            """)
        
    def setup_controls(self):
        """Add Filter-specific controls."""
        # INI state: LP, SER, 60% freq, 30% reso, 50% mix
        self.f1_knob, self.f1_mode_label = self._add_filter_knob("F1", 120, self.f1_mode_index, "Filter 1 frequency")
        self.r1_knob = self.add_knob("R1", 60, "Filter 1 resonance")
        self.f2_knob, self.f2_mode_label = self._add_filter_knob("F2", 120, self.f2_mode_index, "Filter 2 frequency")
        self.r2_knob = self.add_knob("R2", 60, "Filter 2 resonance")
        self.mix_knob = self.add_knob("MIX", 100, "Dry/Wet mix")
        
        # Connect mode labels to cycle
        self.f1_mode_label.mousePressEvent = self._cycle_f1_mode
        self.f2_mode_label.mousePressEvent = self._cycle_f2_mode
        
        # Bottom row: Routing + Sync buttons + AMT
        # Small routing button
        self.routing_btn = QPushButton(self.ROUTINGS[0])
        self.routing_btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['micro']))
        self.routing_btn.setFixedSize(24, 16)
        self.routing_btn.setToolTip("Serial/Parallel routing")
        self.routing_btn.clicked.connect(self._toggle_routing)
        self._update_routing_style()
        self.bottom_layout.addWidget(self.routing_btn)
        
        # Sync buttons
        self.f1_sync_btn = self._create_sync_btn("F1")
        self.f1_sync_btn.index_changed.connect(self._on_f1_sync_changed)
        self.bottom_layout.addWidget(self.f1_sync_btn)
        
        self.f2_sync_btn = self._create_sync_btn("F2")
        self.f2_sync_btn.index_changed.connect(self._on_f2_sync_changed)
        self.bottom_layout.addWidget(self.f2_sync_btn)
        
        # CLK AMT knob for sync depth (small)
        amt_container = QVBoxLayout()
        amt_container.setSpacing(1)
        amt_container.setContentsMargins(0, 0, 0, 0)
        self.amt_knob = MiniKnob()
        self.amt_knob.setObjectName("fx_filter_clk_amt")
        self.amt_knob.setFixedSize(20, 20)
        self.amt_knob.setValue(0)
        self.amt_knob.setToolTip("Clock sync modulation depth")
        amt_container.addWidget(self.amt_knob, alignment=Qt.AlignCenter)
        amt_label = QLabel("CLK")
        amt_label.setFont(QFont(MONO_FONT, FONT_SIZES['micro']))
        amt_label.setStyleSheet(f"color: {COLORS['text_dim']};")
        amt_label.setAlignment(Qt.AlignCenter)
        amt_container.addWidget(amt_label)
        self.bottom_layout.addLayout(amt_container)
        
        # Connect knobs
        self.f1_knob.valueChanged.connect(
            lambda v: self._send_osc(OSC_PATHS['fb_freq1'], v / 200.0))
        self.r1_knob.valueChanged.connect(
            lambda v: self._send_osc(OSC_PATHS['fb_reso1'], v / 200.0))
        self.f2_knob.valueChanged.connect(
            lambda v: self._send_osc(OSC_PATHS['fb_freq2'], v / 200.0))
        self.r2_knob.valueChanged.connect(
            lambda v: self._send_osc(OSC_PATHS['fb_reso2'], v / 200.0))
        self.mix_knob.valueChanged.connect(
            lambda v: self._send_osc(OSC_PATHS['fb_mix'], v / 200.0))
        self.amt_knob.valueChanged.connect(
            lambda v: self._send_osc(OSC_PATHS['fb_sync_amt'], v / 200.0))
    
    def _update_routing_style(self):
        """Update routing button appearance."""
        self.routing_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['background_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 2px;
                padding: 0px;
            }}
            QPushButton:hover {{
                border-color: {COLORS['text_dim']};
            }}
        """)
    
    def _cycle_f1_mode(self, event):
        """Cycle F1 filter mode."""
        self.f1_mode_index = (self.f1_mode_index + 1) % len(self.MODES)
        self.f1_mode_label.setText(self.MODES[self.f1_mode_index])
        self._send_osc(OSC_PATHS['fb_mode1'], self.f1_mode_index)
    
    def _cycle_f2_mode(self, event):
        """Cycle F2 filter mode."""
        self.f2_mode_index = (self.f2_mode_index + 1) % len(self.MODES)
        self.f2_mode_label.setText(self.MODES[self.f2_mode_index])
        self._send_osc(OSC_PATHS['fb_mode2'], self.f2_mode_index)
    
    def _on_f1_sync_changed(self, index):
        """Handle F1 sync rate change."""
        # If clicked from FREE (prev=0, now=1), jump to CLK instead
        if self.f1_prev_sync == 0 and index == 1:
            index = FILTER_SYNC_CLK_INDEX
            self.f1_sync_btn.set_index(index)
        
        self.f1_prev_sync = index
        self._update_sync_btn_style(self.f1_sync_btn, index)
        rate = FILTER_SYNC_MODES[index]
        self._send_osc(OSC_PATHS['fb_sync1'], "" if rate == "FREE" else rate)
    
    def _on_f2_sync_changed(self, index):
        """Handle F2 sync rate change."""
        # If clicked from FREE (prev=0, now=1), jump to CLK instead
        if self.f2_prev_sync == 0 and index == 1:
            index = FILTER_SYNC_CLK_INDEX
            self.f2_sync_btn.set_index(index)
        
        self.f2_prev_sync = index
        self._update_sync_btn_style(self.f2_sync_btn, index)
        rate = FILTER_SYNC_MODES[index]
        self._send_osc(OSC_PATHS['fb_sync2'], "" if rate == "FREE" else rate)
            
    def _toggle_routing(self):
        """Toggle between serial and parallel routing."""
        self.routing_index = 1 - self.routing_index
        self.routing_btn.setText(self.ROUTINGS[self.routing_index])
        self._send_osc(OSC_PATHS['fb_routing'], self.routing_index)
        
    def _on_bypass_changed(self):
        """Send bypass state."""
        self._send_osc(OSC_PATHS['fb_bypass'], 1 if self.bypassed else 0)
    
    def _apply_turbo(self):
        """Apply turbo presets for Filter. Scaled from INI: 60%/30%/50% → 75%/50%/75% → 90%/70%/100%."""
        if self.turbo_state == self.TURBO_OFF:
            # INI: LP SER, 60% freq, 30% reso, 50% mix, no sync depth
            self._drive_value = 0.0
            self._harmonics_value = 0
            self._send_osc(OSC_PATHS['fb_drive'], self._drive_value)
            self._send_osc(OSC_PATHS['fb_harmonics'], self._harmonics_value)
            self.f1_knob.setValue(120)  # 60%
            self.f2_knob.setValue(120)
            self.r1_knob.setValue(60)   # 30%
            self.r2_knob.setValue(60)
            self.mix_knob.setValue(100)  # 50%
            self.amt_knob.setValue(0)    # No sync effect
        elif self.turbo_state == self.TURBO_T1:
            # T1: 75% freq, 50% reso, 75% mix, 50% sync depth
            self._drive_value = 0.2
            self._harmonics_value = 0
            self._send_osc(OSC_PATHS['fb_drive'], self._drive_value)
            self._send_osc(OSC_PATHS['fb_harmonics'], self._harmonics_value)
            self.f1_knob.setValue(150)  # 75%
            self.f2_knob.setValue(150)
            self.r1_knob.setValue(100)  # 50%
            self.r2_knob.setValue(100)
            self.mix_knob.setValue(150)  # 75%
            self.amt_knob.setValue(100)  # 50% sync
        else:  # T2
            # T2: 90% freq, 70% reso, 100% mix, full sync depth
            self._drive_value = 0.5
            self._harmonics_value = 1
            self._send_osc(OSC_PATHS['fb_drive'], self._drive_value)
            self._send_osc(OSC_PATHS['fb_harmonics'], self._harmonics_value)
            self.f1_knob.setValue(180)  # 90%
            self.f2_knob.setValue(180)
            self.r1_knob.setValue(140)  # 70%
            self.r2_knob.setValue(140)
            self.mix_knob.setValue(200)  # 100%
            self.amt_knob.setValue(200)  # Full sync
    
    def sync_state(self):
        """Sync all Filter state to SC on reconnect."""
        # Bypass
        self._send_osc(OSC_PATHS['fb_bypass'], 1 if self.bypassed else 0)
        
        # Knobs
        self._send_osc(OSC_PATHS['fb_freq1'], self.f1_knob.value() / 200.0)
        self._send_osc(OSC_PATHS['fb_reso1'], self.r1_knob.value() / 200.0)
        self._send_osc(OSC_PATHS['fb_freq2'], self.f2_knob.value() / 200.0)
        self._send_osc(OSC_PATHS['fb_reso2'], self.r2_knob.value() / 200.0)
        self._send_osc(OSC_PATHS['fb_mix'], self.mix_knob.value() / 200.0)
        self._send_osc(OSC_PATHS['fb_sync_amt'], self.amt_knob.value() / 200.0)
        
        # Mode/routing
        self._send_osc(OSC_PATHS['fb_mode1'], self.f1_mode_index)
        self._send_osc(OSC_PATHS['fb_mode2'], self.f2_mode_index)
        self._send_osc(OSC_PATHS['fb_routing'], self.routing_index)
        
        # Sync rates
        rate1 = FILTER_SYNC_MODES[self.f1_sync_btn.index]
        rate2 = FILTER_SYNC_MODES[self.f2_sync_btn.index]
        self._send_osc(OSC_PATHS['fb_sync1'], "" if rate1 == "FREE" else rate1)
        self._send_osc(OSC_PATHS['fb_sync2'], "" if rate2 == "FREE" else rate2)
        
        # Turbo-only params (drive, harmonics)
        self._send_osc(OSC_PATHS['fb_drive'], self._drive_value)
        self._send_osc(OSC_PATHS['fb_harmonics'], self._harmonics_value)


class InlineFXStrip(QWidget):
    """
    Compact horizontal FX strip for bottom banner.
    Shows key controls for each FX module with bypass and turbo toggles.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.osc_bridge = None
        self.modules = {}
        self.setup_ui()
        
    def setup_ui(self):
        """Create inline FX strip."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # FX Modules - fixed sizes
        self.heat = HeatModule()
        self.heat.setFixedWidth(110)
        self.heat.setFixedHeight(170)
        layout.addWidget(self.heat)
        self.modules['HEAT'] = self.heat
        
        layout.addWidget(self._separator())
        
        self.echo = EchoModule()
        self.echo.setFixedWidth(155)
        self.echo.setFixedHeight(170)
        layout.addWidget(self.echo)
        self.modules['ECHO'] = self.echo
        
        layout.addWidget(self._separator())
        
        self.reverb = ReverbModule()
        self.reverb.setFixedWidth(160)
        self.reverb.setFixedHeight(170)
        layout.addWidget(self.reverb)
        self.modules['REVERB'] = self.reverb
        
        layout.addWidget(self._separator())
        
        self.filter = FilterModule()
        self.filter.setFixedWidth(155)
        self.filter.setFixedHeight(170)
        layout.addWidget(self.filter)
        self.modules['FILTER'] = self.filter
        
    def _separator(self):
        """Create vertical separator."""
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFixedWidth(1)
        sep.setStyleSheet(f"color: {COLORS['border']};")
        sep.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        return sep
        
    def set_osc_bridge(self, osc_bridge):
        """Set OSC bridge for all modules."""
        self.osc_bridge = osc_bridge
        for module in self.modules.values():
            module.set_osc_bridge(osc_bridge)
    
    def sync_state(self):
        """Sync all FX module state to SC on reconnect."""
        for module in self.modules.values():
            module.sync_state()
