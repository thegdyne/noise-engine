"""
FX Window
Master FX controls: Heat, Tape Echo, Reverb, Dual Filter
"""
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QPushButton, QComboBox, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from .theme import COLORS, FONT_FAMILY, FONT_SIZES
from .widgets import DragSlider
from src.config import SIZES, OSC_PATHS


class FXSection(QFrame):
    """Base class for FX module sections."""
    
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.StyledPanel)
        self.setStyleSheet(f"""
            FXSection {{
                background-color: {COLORS['background']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
            }}
        """)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(8, 6, 8, 8)
        self.layout.setSpacing(6)
        
        # Header
        header = QHBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont(FONT_FAMILY, FONT_SIZES['small'], QFont.Bold))
        self.title_label.setStyleSheet(f"color: {COLORS['text']};")
        header.addWidget(self.title_label)
        header.addStretch()
        
        self.bypass_btn = QPushButton("ON")
        self.bypass_btn.setFont(QFont(FONT_FAMILY, FONT_SIZES['tiny']))
        self.bypass_btn.setFixedSize(32, 18)
        self.bypass_btn.clicked.connect(self._on_bypass_clicked)
        header.addWidget(self.bypass_btn)
        
        self.layout.addLayout(header)
        
        # Controls container
        self.controls = QHBoxLayout()
        self.controls.setSpacing(8)
        self.layout.addLayout(self.controls)
        
        self._bypassed = True
        self._update_bypass_style()
    
    def _on_bypass_clicked(self):
        self._bypassed = not self._bypassed
        self._update_bypass_style()
        self.on_bypass_changed(self._bypassed)
    
    def _update_bypass_style(self):
        if not self._bypassed:
            self.bypass_btn.setText("ON")
            self.bypass_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['accent_effect']};
                    color: {COLORS['background']};
                    border: none;
                    border-radius: 2px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['accent_effect']};
                }}
            """)
        else:
            self.bypass_btn.setText("BYP")
            self.bypass_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['background_light']};
                    color: {COLORS['text_dim']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 2px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['border']};
                }}
            """)
    
    def on_bypass_changed(self, bypassed):
        """Override in subclass."""
        pass
    
    def add_knob(self, label, min_val=0, max_val=100, default=50):
        """Add a labeled knob to controls."""
        container = QVBoxLayout()
        container.setSpacing(2)
        
        knob = DragSlider()
        knob.setRange(min_val, max_val)
        knob.setValue(default)
        knob.setFixedSize(28, 50)
        
        lbl = QLabel(label)
        lbl.setFont(QFont(FONT_FAMILY, FONT_SIZES['micro']))
        lbl.setStyleSheet(f"color: {COLORS['text_dim']};")
        lbl.setAlignment(Qt.AlignCenter)
        
        container.addWidget(knob, alignment=Qt.AlignCenter)
        container.addWidget(lbl, alignment=Qt.AlignCenter)
        self.controls.addLayout(container)
        
        return knob


class HeatSection(FXSection):
    """Heat saturation controls."""
    
    bypass_changed = pyqtSignal(int)
    circuit_changed = pyqtSignal(int)
    drive_changed = pyqtSignal(float)
    mix_changed = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__("HEAT", parent)
        
        # Circuit selector
        circuit_container = QVBoxLayout()
        circuit_container.setSpacing(2)
        
        self.circuit_combo = QComboBox()
        self.circuit_combo.addItems(["CLEAN", "TAPE", "TUBE", "CRUNCH"])
        self.circuit_combo.setFont(QFont(FONT_FAMILY, FONT_SIZES['tiny']))
        self.circuit_combo.setFixedWidth(70)
        self.circuit_combo.currentIndexChanged.connect(lambda i: self.circuit_changed.emit(i))
        
        circuit_lbl = QLabel("CIRCUIT")
        circuit_lbl.setFont(QFont(FONT_FAMILY, FONT_SIZES['micro']))
        circuit_lbl.setStyleSheet(f"color: {COLORS['text_dim']};")
        circuit_lbl.setAlignment(Qt.AlignCenter)
        
        circuit_container.addWidget(self.circuit_combo, alignment=Qt.AlignCenter)
        circuit_container.addWidget(circuit_lbl, alignment=Qt.AlignCenter)
        self.controls.addLayout(circuit_container)
        
        # Knobs
        self.drive_knob = self.add_knob("DRIVE", 0, 100, 0)
        self.drive_knob.valueChanged.connect(lambda v: self.drive_changed.emit(v / 100.0))
        
        self.mix_knob = self.add_knob("MIX", 0, 100, 100)
        self.mix_knob.valueChanged.connect(lambda v: self.mix_changed.emit(v / 100.0))
    
    def on_bypass_changed(self, bypassed):
        self.bypass_changed.emit(1 if bypassed else 0)


class TapeEchoSection(FXSection):
    """Tape Echo delay controls."""
    
    time_changed = pyqtSignal(float)
    feedback_changed = pyqtSignal(float)
    tone_changed = pyqtSignal(float)
    wow_changed = pyqtSignal(float)
    spring_changed = pyqtSignal(float)
    verb_send_changed = pyqtSignal(float)
    return_changed = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__("TAPE ECHO", parent)
        # No bypass for send effects - always on
        self.bypass_btn.hide()
        
        self.time_knob = self.add_knob("TIME", 0, 100, 40)
        self.time_knob.valueChanged.connect(lambda v: self.time_changed.emit(v / 100.0))
        
        self.feedback_knob = self.add_knob("FDBK", 0, 100, 30)
        self.feedback_knob.valueChanged.connect(lambda v: self.feedback_changed.emit(v / 100.0))
        
        self.tone_knob = self.add_knob("TONE", 0, 100, 70)
        self.tone_knob.valueChanged.connect(lambda v: self.tone_changed.emit(v / 100.0))
        
        self.wow_knob = self.add_knob("WOW", 0, 100, 10)
        self.wow_knob.valueChanged.connect(lambda v: self.wow_changed.emit(v / 100.0))
        
        self.spring_knob = self.add_knob("SPRING", 0, 100, 0)
        self.spring_knob.valueChanged.connect(lambda v: self.spring_changed.emit(v / 100.0))
        
        self.verb_send_knob = self.add_knob("â†’VRB", 0, 100, 0)
        self.verb_send_knob.valueChanged.connect(lambda v: self.verb_send_changed.emit(v / 100.0))
        
        self.return_knob = self.add_knob("RTN", 0, 100, 50)
        self.return_knob.valueChanged.connect(lambda v: self.return_changed.emit(v / 100.0))


class ReverbSection(FXSection):
    """Reverb controls."""
    
    size_changed = pyqtSignal(float)
    decay_changed = pyqtSignal(float)
    tone_changed = pyqtSignal(float)
    return_changed = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__("REVERB", parent)
        # No bypass for send effects
        self.bypass_btn.hide()
        
        self.size_knob = self.add_knob("SIZE", 0, 100, 50)
        self.size_knob.valueChanged.connect(lambda v: self.size_changed.emit(v / 100.0))
        
        self.decay_knob = self.add_knob("DECAY", 0, 100, 50)
        self.decay_knob.valueChanged.connect(lambda v: self.decay_changed.emit(v / 100.0))
        
        self.tone_knob = self.add_knob("TONE", 0, 100, 70)
        self.tone_knob.valueChanged.connect(lambda v: self.tone_changed.emit(v / 100.0))
        
        self.return_knob = self.add_knob("RTN", 0, 100, 30)
        self.return_knob.valueChanged.connect(lambda v: self.return_changed.emit(v / 100.0))


class DualFilterSection(FXSection):
    """Dual Filter controls."""
    
    bypass_changed = pyqtSignal(int)
    drive_changed = pyqtSignal(float)
    freq1_changed = pyqtSignal(float)
    reso1_changed = pyqtSignal(float)
    mode1_changed = pyqtSignal(int)
    freq2_changed = pyqtSignal(float)
    reso2_changed = pyqtSignal(float)
    mode2_changed = pyqtSignal(int)
    harmonics_changed = pyqtSignal(int)
    routing_changed = pyqtSignal(int)
    mix_changed = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__("DUAL FILTER", parent)
        
        # Drive
        self.drive_knob = self.add_knob("DRIVE", 0, 100, 0)
        self.drive_knob.valueChanged.connect(lambda v: self.drive_changed.emit(v / 100.0))
        
        # Filter 1
        self.freq1_knob = self.add_knob("F1", 0, 100, 50)
        self.freq1_knob.valueChanged.connect(lambda v: self.freq1_changed.emit(v / 100.0))
        
        self.reso1_knob = self.add_knob("R1", 0, 100, 0)
        self.reso1_knob.valueChanged.connect(lambda v: self.reso1_changed.emit(v / 100.0))
        
        # Mode 1 combo
        mode1_container = QVBoxLayout()
        mode1_container.setSpacing(2)
        self.mode1_combo = QComboBox()
        self.mode1_combo.addItems(["LP", "BP", "HP"])
        self.mode1_combo.setCurrentIndex(1)  # BP default
        self.mode1_combo.setFont(QFont(FONT_FAMILY, FONT_SIZES['tiny']))
        self.mode1_combo.setFixedWidth(40)
        self.mode1_combo.currentIndexChanged.connect(lambda i: self.mode1_changed.emit(i))
        mode1_lbl = QLabel("M1")
        mode1_lbl.setFont(QFont(FONT_FAMILY, FONT_SIZES['micro']))
        mode1_lbl.setStyleSheet(f"color: {COLORS['text_dim']};")
        mode1_lbl.setAlignment(Qt.AlignCenter)
        mode1_container.addWidget(self.mode1_combo, alignment=Qt.AlignCenter)
        mode1_container.addWidget(mode1_lbl, alignment=Qt.AlignCenter)
        self.controls.addLayout(mode1_container)
        
        # Filter 2
        self.freq2_knob = self.add_knob("F2", 0, 100, 35)
        self.freq2_knob.valueChanged.connect(lambda v: self.freq2_changed.emit(v / 100.0))
        
        self.reso2_knob = self.add_knob("R2", 0, 100, 0)
        self.reso2_knob.valueChanged.connect(lambda v: self.reso2_changed.emit(v / 100.0))
        
        # Mode 2 combo
        mode2_container = QVBoxLayout()
        mode2_container.setSpacing(2)
        self.mode2_combo = QComboBox()
        self.mode2_combo.addItems(["LP", "BP", "HP"])
        self.mode2_combo.setCurrentIndex(1)
        self.mode2_combo.setFont(QFont(FONT_FAMILY, FONT_SIZES['tiny']))
        self.mode2_combo.setFixedWidth(40)
        self.mode2_combo.currentIndexChanged.connect(lambda i: self.mode2_changed.emit(i))
        mode2_lbl = QLabel("M2")
        mode2_lbl.setFont(QFont(FONT_FAMILY, FONT_SIZES['micro']))
        mode2_lbl.setStyleSheet(f"color: {COLORS['text_dim']};")
        mode2_lbl.setAlignment(Qt.AlignCenter)
        mode2_container.addWidget(self.mode2_combo, alignment=Qt.AlignCenter)
        mode2_container.addWidget(mode2_lbl, alignment=Qt.AlignCenter)
        self.controls.addLayout(mode2_container)
        
        # Harmonics
        harm_container = QVBoxLayout()
        harm_container.setSpacing(2)
        self.harmonics_combo = QComboBox()
        self.harmonics_combo.addItems(["Free", "1", "2", "3", "4", "5", "8", "16"])
        self.harmonics_combo.setFont(QFont(FONT_FAMILY, FONT_SIZES['tiny']))
        self.harmonics_combo.setFixedWidth(50)
        self.harmonics_combo.currentIndexChanged.connect(lambda i: self.harmonics_changed.emit(i))
        harm_lbl = QLabel("SYNC")
        harm_lbl.setFont(QFont(FONT_FAMILY, FONT_SIZES['micro']))
        harm_lbl.setStyleSheet(f"color: {COLORS['text_dim']};")
        harm_lbl.setAlignment(Qt.AlignCenter)
        harm_container.addWidget(self.harmonics_combo, alignment=Qt.AlignCenter)
        harm_container.addWidget(harm_lbl, alignment=Qt.AlignCenter)
        self.controls.addLayout(harm_container)
        
        # Routing
        route_container = QVBoxLayout()
        route_container.setSpacing(2)
        self.routing_combo = QComboBox()
        self.routing_combo.addItems(["SER", "PAR"])
        self.routing_combo.setFont(QFont(FONT_FAMILY, FONT_SIZES['tiny']))
        self.routing_combo.setFixedWidth(45)
        self.routing_combo.currentIndexChanged.connect(lambda i: self.routing_changed.emit(i))
        route_lbl = QLabel("ROUTE")
        route_lbl.setFont(QFont(FONT_FAMILY, FONT_SIZES['micro']))
        route_lbl.setStyleSheet(f"color: {COLORS['text_dim']};")
        route_lbl.setAlignment(Qt.AlignCenter)
        route_container.addWidget(self.routing_combo, alignment=Qt.AlignCenter)
        route_container.addWidget(route_lbl, alignment=Qt.AlignCenter)
        self.controls.addLayout(route_container)
        
        # Mix
        self.mix_knob = self.add_knob("MIX", 0, 100, 100)
        self.mix_knob.valueChanged.connect(lambda v: self.mix_changed.emit(v / 100.0))
    
    def on_bypass_changed(self, bypassed):
        self.bypass_changed.emit(1 if bypassed else 0)


class FXWindow(QMainWindow):
    """Master FX control window."""
    
    def __init__(self, osc_bridge=None, parent=None):
        super().__init__(parent)
        self.osc_bridge = osc_bridge
        self._signals_connected = False
        
        self.setWindowTitle("Master FX")
        self.setMinimumSize(500, 400)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        
        # Sections
        self.heat = HeatSection()
        self.tape_echo = TapeEchoSection()
        self.reverb = ReverbSection()
        self.dual_filter = DualFilterSection()
        
        layout.addWidget(self.heat)
        layout.addWidget(self.tape_echo)
        layout.addWidget(self.reverb)
        layout.addWidget(self.dual_filter)
        layout.addStretch()
        
        # Connect signals
        self._connect_signals()
        
        # Style
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {COLORS['background']};
            }}
            QComboBox {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 2px;
                padding: 2px 4px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 12px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
                selection-background-color: {COLORS['accent_effect']};
            }}
        """)
    
    def _send_osc(self, path, value):
        """Send OSC if connected."""
        if self.osc_bridge and self.osc_bridge.client:
            self.osc_bridge.client.send_message(path, [value])
    
    def set_osc_bridge(self, osc_bridge):
        """Set OSC bridge for communication with SuperCollider."""
        self.osc_bridge = osc_bridge
        # Signals are already connected via lambdas that check osc_bridge
        # Sync current state to SC
        if osc_bridge:
            self._sync_to_sc()
    
    def _connect_signals(self):
        """Connect UI signals to OSC."""
        if self._signals_connected:
            return
        self._signals_connected = True
        
        # Heat
        self.heat.bypass_changed.connect(
            lambda v: self._send_osc(OSC_PATHS['heat_bypass'], v))
        self.heat.circuit_changed.connect(
            lambda v: self._send_osc(OSC_PATHS['heat_circuit'], v))
        self.heat.drive_changed.connect(
            lambda v: self._send_osc(OSC_PATHS['heat_drive'], v))
        self.heat.mix_changed.connect(
            lambda v: self._send_osc(OSC_PATHS['heat_mix'], v))
        
        # Tape Echo
        self.tape_echo.time_changed.connect(
            lambda v: self._send_osc(OSC_PATHS['echo_time'], v))
        self.tape_echo.feedback_changed.connect(
            lambda v: self._send_osc(OSC_PATHS['echo_feedback'], v))
        self.tape_echo.tone_changed.connect(
            lambda v: self._send_osc(OSC_PATHS['echo_tone'], v))
        self.tape_echo.wow_changed.connect(
            lambda v: self._send_osc(OSC_PATHS['echo_wow'], v))
        self.tape_echo.spring_changed.connect(
            lambda v: self._send_osc(OSC_PATHS['echo_spring'], v))
        self.tape_echo.verb_send_changed.connect(
            lambda v: self._send_osc(OSC_PATHS['echo_verb_send'], v))
        self.tape_echo.return_changed.connect(
            lambda v: self._send_osc(OSC_PATHS['master_echo_return'], v))
        
        # Reverb
        self.reverb.size_changed.connect(
            lambda v: self._send_osc(OSC_PATHS['verb_size'], v))
        self.reverb.decay_changed.connect(
            lambda v: self._send_osc(OSC_PATHS['verb_decay'], v))
        self.reverb.tone_changed.connect(
            lambda v: self._send_osc(OSC_PATHS['verb_tone'], v))
        self.reverb.return_changed.connect(
            lambda v: self._send_osc(OSC_PATHS['master_verb_return'], v))
        
        # Dual Filter
        self.dual_filter.bypass_changed.connect(
            lambda v: self._send_osc(OSC_PATHS['fb_bypass'], v))
        self.dual_filter.drive_changed.connect(
            lambda v: self._send_osc(OSC_PATHS['fb_drive'], v))
        self.dual_filter.freq1_changed.connect(
            lambda v: self._send_osc(OSC_PATHS['fb_freq1'], v))
        self.dual_filter.reso1_changed.connect(
            lambda v: self._send_osc(OSC_PATHS['fb_reso1'], v))
        self.dual_filter.mode1_changed.connect(
            lambda v: self._send_osc(OSC_PATHS['fb_mode1'], v))
        self.dual_filter.freq2_changed.connect(
            lambda v: self._send_osc(OSC_PATHS['fb_freq2'], v))
        self.dual_filter.reso2_changed.connect(
            lambda v: self._send_osc(OSC_PATHS['fb_reso2'], v))
        self.dual_filter.mode2_changed.connect(
            lambda v: self._send_osc(OSC_PATHS['fb_mode2'], v))
        self.dual_filter.harmonics_changed.connect(
            lambda v: self._send_osc(OSC_PATHS['fb_harmonics'], v))
        self.dual_filter.routing_changed.connect(
            lambda v: self._send_osc(OSC_PATHS['fb_routing'], v))
        self.dual_filter.mix_changed.connect(
            lambda v: self._send_osc(OSC_PATHS['fb_mix'], v))

    # â”€â”€ Preset State Methods â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def get_state(self):
        """Collect current FX state from all sections.
        
        Returns:
            FXState: Current state of all FX controls
        """
        from src.presets.preset_schema import FXState, HeatState, EchoState, ReverbState, DualFilterState
        
        return FXState(
            heat=HeatState(
                bypass=self.heat._bypassed,
                circuit=self.heat.circuit_combo.currentIndex(),
                drive=self.heat.drive_knob.value(),
                mix=self.heat.mix_knob.value()
            ),
            echo=EchoState(
                time=self.tape_echo.time_knob.value(),
                feedback=self.tape_echo.feedback_knob.value(),
                tone=self.tape_echo.tone_knob.value(),
                wow=self.tape_echo.wow_knob.value(),
                spring=self.tape_echo.spring_knob.value(),
                verb_send=self.tape_echo.verb_send_knob.value(),
                return_level=self.tape_echo.return_knob.value()
            ),
            reverb=ReverbState(
                size=self.reverb.size_knob.value(),
                decay=self.reverb.decay_knob.value(),
                tone=self.reverb.tone_knob.value(),
                return_level=self.reverb.return_knob.value()
            ),
            dual_filter=DualFilterState(
                bypass=self.dual_filter._bypassed,
                drive=self.dual_filter.drive_knob.value(),
                freq1=self.dual_filter.freq1_knob.value(),
                reso1=self.dual_filter.reso1_knob.value(),
                mode1=self.dual_filter.mode1_combo.currentIndex(),
                freq2=self.dual_filter.freq2_knob.value(),
                reso2=self.dual_filter.reso2_knob.value(),
                mode2=self.dual_filter.mode2_combo.currentIndex(),
                harmonics=self.dual_filter.harmonics_combo.currentIndex(),
                routing=self.dual_filter.routing_combo.currentIndex(),
                mix=self.dual_filter.mix_knob.value()
            )
        )

    def set_state(self, fx):
        """Apply FX state to all sections.
        
        Args:
            fx: FXState dataclass with heat, echo, reverb, dual_filter
        """
        # Block signals during state restore to avoid triggering OSC
        self._block_all_signals(True)
        
        try:
            # Heat
            self.heat._bypassed = fx.heat.bypass
            self.heat._update_bypass_style()
            self.heat.circuit_combo.setCurrentIndex(fx.heat.circuit)
            self.heat.drive_knob.setValue(fx.heat.drive)
            self.heat.mix_knob.setValue(fx.heat.mix)
            
            # Echo
            self.tape_echo.time_knob.setValue(fx.echo.time)
            self.tape_echo.feedback_knob.setValue(fx.echo.feedback)
            self.tape_echo.tone_knob.setValue(fx.echo.tone)
            self.tape_echo.wow_knob.setValue(fx.echo.wow)
            self.tape_echo.spring_knob.setValue(fx.echo.spring)
            self.tape_echo.verb_send_knob.setValue(fx.echo.verb_send)
            self.tape_echo.return_knob.setValue(fx.echo.return_level)
            
            # Reverb
            self.reverb.size_knob.setValue(fx.reverb.size)
            self.reverb.decay_knob.setValue(fx.reverb.decay)
            self.reverb.tone_knob.setValue(fx.reverb.tone)
            self.reverb.return_knob.setValue(fx.reverb.return_level)
            
            # Dual Filter
            self.dual_filter._bypassed = fx.dual_filter.bypass
            self.dual_filter._update_bypass_style()
            self.dual_filter.drive_knob.setValue(fx.dual_filter.drive)
            self.dual_filter.freq1_knob.setValue(fx.dual_filter.freq1)
            self.dual_filter.reso1_knob.setValue(fx.dual_filter.reso1)
            self.dual_filter.mode1_combo.setCurrentIndex(fx.dual_filter.mode1)
            self.dual_filter.freq2_knob.setValue(fx.dual_filter.freq2)
            self.dual_filter.reso2_knob.setValue(fx.dual_filter.reso2)
            self.dual_filter.mode2_combo.setCurrentIndex(fx.dual_filter.mode2)
            self.dual_filter.harmonics_combo.setCurrentIndex(fx.dual_filter.harmonics)
            self.dual_filter.routing_combo.setCurrentIndex(fx.dual_filter.routing)
            self.dual_filter.mix_knob.setValue(fx.dual_filter.mix)
        finally:
            self._block_all_signals(False)
        
        # Now send all values to SuperCollider
        self._sync_to_sc()

    def _block_all_signals(self, block):
        """Block/unblock signals on all controls."""
        # Heat
        self.heat.circuit_combo.blockSignals(block)
        self.heat.drive_knob.blockSignals(block)
        self.heat.mix_knob.blockSignals(block)
        
        # Echo
        self.tape_echo.time_knob.blockSignals(block)
        self.tape_echo.feedback_knob.blockSignals(block)
        self.tape_echo.tone_knob.blockSignals(block)
        self.tape_echo.wow_knob.blockSignals(block)
        self.tape_echo.spring_knob.blockSignals(block)
        self.tape_echo.verb_send_knob.blockSignals(block)
        self.tape_echo.return_knob.blockSignals(block)
        
        # Reverb
        self.reverb.size_knob.blockSignals(block)
        self.reverb.decay_knob.blockSignals(block)
        self.reverb.tone_knob.blockSignals(block)
        self.reverb.return_knob.blockSignals(block)
        
        # Dual Filter
        self.dual_filter.drive_knob.blockSignals(block)
        self.dual_filter.freq1_knob.blockSignals(block)
        self.dual_filter.reso1_knob.blockSignals(block)
        self.dual_filter.mode1_combo.blockSignals(block)
        self.dual_filter.freq2_knob.blockSignals(block)
        self.dual_filter.reso2_knob.blockSignals(block)
        self.dual_filter.mode2_combo.blockSignals(block)
        self.dual_filter.harmonics_combo.blockSignals(block)
        self.dual_filter.routing_combo.blockSignals(block)
        self.dual_filter.mix_knob.blockSignals(block)

    def _sync_to_sc(self):
        """Send all current FX values to SuperCollider."""
        if not self.osc_bridge or not self.osc_bridge.client:
            return
        
        # Heat
        self._send_osc(OSC_PATHS['heat_bypass'], 1 if self.heat._bypassed else 0)
        self._send_osc(OSC_PATHS['heat_circuit'], self.heat.circuit_combo.currentIndex())
        self._send_osc(OSC_PATHS['heat_drive'], self.heat.drive_knob.value() / 100.0)
        self._send_osc(OSC_PATHS['heat_mix'], self.heat.mix_knob.value() / 100.0)
        
        # Echo
        self._send_osc(OSC_PATHS['echo_time'], self.tape_echo.time_knob.value() / 100.0)
        self._send_osc(OSC_PATHS['echo_feedback'], self.tape_echo.feedback_knob.value() / 100.0)
        self._send_osc(OSC_PATHS['echo_tone'], self.tape_echo.tone_knob.value() / 100.0)
        self._send_osc(OSC_PATHS['echo_wow'], self.tape_echo.wow_knob.value() / 100.0)
        self._send_osc(OSC_PATHS['echo_spring'], self.tape_echo.spring_knob.value() / 100.0)
        self._send_osc(OSC_PATHS['echo_verb_send'], self.tape_echo.verb_send_knob.value() / 100.0)
        self._send_osc(OSC_PATHS['master_echo_return'], self.tape_echo.return_knob.value() / 100.0)
        
        # Reverb
        self._send_osc(OSC_PATHS['verb_size'], self.reverb.size_knob.value() / 100.0)
        self._send_osc(OSC_PATHS['verb_decay'], self.reverb.decay_knob.value() / 100.0)
        self._send_osc(OSC_PATHS['verb_tone'], self.reverb.tone_knob.value() / 100.0)
        self._send_osc(OSC_PATHS['master_verb_return'], self.reverb.return_knob.value() / 100.0)
        
        # Dual Filter
        self._send_osc(OSC_PATHS['fb_bypass'], 1 if self.dual_filter._bypassed else 0)
        self._send_osc(OSC_PATHS['fb_drive'], self.dual_filter.drive_knob.value() / 100.0)
        self._send_osc(OSC_PATHS['fb_freq1'], self.dual_filter.freq1_knob.value() / 100.0)
        self._send_osc(OSC_PATHS['fb_reso1'], self.dual_filter.reso1_knob.value() / 100.0)
        self._send_osc(OSC_PATHS['fb_mode1'], self.dual_filter.mode1_combo.currentIndex())
        self._send_osc(OSC_PATHS['fb_freq2'], self.dual_filter.freq2_knob.value() / 100.0)
        self._send_osc(OSC_PATHS['fb_reso2'], self.dual_filter.reso2_knob.value() / 100.0)
        self._send_osc(OSC_PATHS['fb_mode2'], self.dual_filter.mode2_combo.currentIndex())
        self._send_osc(OSC_PATHS['fb_harmonics'], self.dual_filter.harmonics_combo.currentIndex())
        self._send_osc(OSC_PATHS['fb_routing'], self.dual_filter.routing_combo.currentIndex())
        self._send_osc(OSC_PATHS['fb_mix'], self.dual_filter.mix_knob.value() / 100.0)
