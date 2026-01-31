"""
Noise Engine Direct OSC Telemetry

Real-time DSP telemetry receiver with phase-locked ideal waveform overlay.
Development tool for generator tuning and debugging.

Usage:
    from telemetry import TelemetryController, TelemetryWidget
    
    controller = TelemetryController(osc_server)
    widget = TelemetryWidget(controller)
    
    # Enable telemetry for slot 0 at 15Hz
    controller.enable(slot=0, rate=15)

OSC Paths:
    /telem/gen  - Control rate data (freq, phase, params, RMS, peak, badValue)
    /telem/wave - Audio rate waveform (128 samples, 1 cycle)

References:
    DIRECT_OSC_TELEMETRY_SPEC.md
"""

import json
import time
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Callable

import numpy as np
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QComboBox, QLabel, QFrame, QSlider,
    QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt, QObject, QTimer, pyqtSignal
from PyQt5.QtGui import QFont

try:
    import pyqtgraph as pg
    HAS_PYQTGRAPH = True
except ImportError:
    HAS_PYQTGRAPH = False
    print("[Telemetry] PyQtGraph not available - overlay disabled")


# =============================================================================
# IDEAL WAVEFORM GENERATOR
# =============================================================================

class IdealOverlay:
    """
    Generates mathematical ideal waveforms for comparison.
    All methods return waveforms that can be phase-aligned to telemetry data.
    """
    
    def __init__(self, n_samples: int = 128):
        self.n_samples = n_samples
        self.t = np.linspace(0, 2 * np.pi, n_samples, endpoint=False)
    
    def align_to_phase(self, waveform: np.ndarray, phase: float) -> np.ndarray:
        """
        Rotate waveform to match current oscillator phase from telemetry.
        
        Args:
            waveform: The ideal waveform array
            phase: Normalized 0-1 phase from SC telemetry
            
        Returns:
            Phase-aligned waveform
        """
        n = len(waveform)
        shift = int(phase * n)
        return np.roll(waveform, -shift)  # Negative to align forward
    
    def ideal_sine(self) -> np.ndarray:
        """Perfect sine wave (phase 0 = zero-crossing rising)."""
        return np.sin(self.t)
    
    def ideal_square(self, duty: float = 0.5) -> np.ndarray:
        """Perfect square wave with adjustable duty cycle."""
        phase_norm = self.t / (2 * np.pi)
        return np.where(phase_norm < duty, 1.0, -1.0).astype(np.float32)
    
    def ideal_saw(self) -> np.ndarray:
        """Perfect sawtooth (ramp up, instant reset)."""
        return (2 * (self.t / (2 * np.pi)) - 1).astype(np.float32)
    
    def ideal_triangle(self) -> np.ndarray:
        """Perfect triangle wave."""
        return (2 * np.abs(2 * (self.t / (2 * np.pi)) - 1) - 1).astype(np.float32)
    
    def ideal_folded_sine(self, fold_amount: float, stages: int = 7) -> np.ndarray:
        """
        Buchla 258-style folded sine.
        
        Args:
            fold_amount: 0.0 = pure sine, 1.0 = fully folded
            stages: Number of fold stages (B258 Master = 7, Extreme = 9)
        
        Returns:
            Folded waveform matching the B258 topology
        """
        sig = np.sin(self.t)
        
        # Match the DSP: drive stage before folding
        drive = 1 + (fold_amount * 5)
        sig = sig * drive
        
        # Cascade fold stages with evolving thresholds
        for i in range(stages):
            threshold = max(0.55, 0.9 - (i * 0.04))
            recovery = 1.08 + (i * 0.01)
            
            # Fold
            sig = np.clip(sig, -threshold, threshold)
            # Tanh recovery (soft saturation)
            sig = np.tanh(sig * recovery)
        
        # Normalize to [-1, 1]
        max_val = np.max(np.abs(sig))
        if max_val > 0:
            sig = sig / max_val
        
        return sig.astype(np.float32)
    
    def ideal_b258_morph(
        self, 
        shape: float, 
        fold: float, 
        sym: float = 0.0,
        drive: float = 0.5
    ) -> np.ndarray:
        """
        Complete B258 dual-morph ideal waveform.
        
        Args:
            shape: 0.0 = folded sine, 1.0 = saw
            fold: Fold intensity (0-1)
            sym: Symmetry offset (-0.5 to 0.5)
            drive: Output saturation (0-1)
        
        Returns:
            Ideal waveform matching the B258 dual-morph topology
        """
        sine = np.sin(self.t)
        
        # Square path (tanh saturation)
        # Strong reciprocal law: fold collapses as shape rises
        fold_effective = fold * ((1 - shape) ** 2)
        sqr_drive = 1 + (fold_effective * 60)
        sqr = np.tanh((sine + sym) * sqr_drive)
        
        # Saw path (with folding)
        saw_raw = 2 * (self.t / (2 * np.pi)) - 1
        saw_blend = sine * (1 - shape) + saw_raw * shape
        saw = np.clip(saw_blend + sym, -0.9, 0.9)
        
        # Unified morph: sine (0) -> square (0.5) -> saw (1.0)
        if shape < 0.5:
            t_blend = shape * 2
            sig = sine * (1 - t_blend) + sqr * t_blend
        else:
            t_blend = (shape - 0.5) * 2
            sig = sqr * (1 - t_blend) + saw * t_blend
        
        # Final saturation
        sat_amount = 1 + (drive * 12)
        sig = np.tanh(sig * sat_amount) / np.tanh(sat_amount)
        
        return sig.astype(np.float32)


# =============================================================================
# TELEMETRY CONTROLLER
# =============================================================================

class TelemetryController(QObject):
    """
    Receives and processes OSC telemetry from SuperCollider.
    
    Signals:
        data_received(int, dict): Emitted when /telem/gen received
        waveform_received(int, np.ndarray): Emitted when /telem/wave received
        core_lock(int, str): Emitted when bad value detected
    """
    
    # Signals
    data_received = pyqtSignal(int, dict)      # slot, data
    waveform_received = pyqtSignal(int, object)  # slot, np.ndarray
    core_lock = pyqtSignal(int, str)           # slot, error_type
    
    def __init__(self, osc_server, sc_client=None, project_root: str = None):
        """
        Initialize telemetry controller.
        
        Args:
            osc_server: OSC server instance with add_handler method
            sc_client: SuperCollider client for sending commands
            project_root: Path to project root for git hash detection
        """
        super().__init__()
        self.osc_server = osc_server
        self.sc_client = sc_client
        self.project_root = project_root or str(Path.home() / "repos" / "noise-engine")
        
        # State
        self.enabled = False
        self.target_slot = 0
        self.current_rate = 15
        
        # History buffer
        self.history: List[Dict] = []
        self.history_max = 300  # ~10 seconds at 30fps
        
        # Waveform buffer
        self.current_waveform: Optional[np.ndarray] = None
        
        # Generator info (set by caller)
        self.current_generator_id: str = ""
        self.current_synthdef_name: str = ""
        self.app_version: str = "1.0.0"
        
        # Register OSC handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register OSC message handlers."""
        if self.osc_server is None:
            return
        
        # Try different handler registration patterns
        if hasattr(self.osc_server, 'add_handler'):
            self.osc_server.add_handler('/telem/gen', self._handle_telemetry)
            self.osc_server.add_handler('/telem/wave', self._handle_waveform)
        elif hasattr(self.osc_server, 'map'):
            # python-osc dispatcher pattern
            self.osc_server.map('/telem/gen', self._handle_telemetry)
            self.osc_server.map('/telem/wave', self._handle_waveform)
    
    def enable(self, slot: int, rate: int = 15):
        """
        Enable telemetry for a specific slot.
        
        Args:
            slot: Generator slot index (0-7)
            rate: Update rate in Hz (5-60, default 15)
        """
        if not 0 <= slot < 8:
            raise ValueError(f"Slot must be 0-7, got {slot}")
        
        rate = max(5, min(60, rate))
        
        self.target_slot = slot
        self.current_rate = rate
        self.enabled = True
        self.history.clear()
        
        # Send OSC to enable telemetry on generator
        self._set_generator_telemetry_rate(slot, rate)
        
        print(f"[Telemetry] Enabled for slot {slot} at {rate}Hz")
    
    def disable(self):
        """Disable telemetry."""
        if self.enabled:
            self._set_generator_telemetry_rate(self.target_slot, 0)
            self.enabled = False
            print("[Telemetry] Disabled")
    
    def set_slot(self, slot: int):
        """Switch to monitoring a different slot."""
        if self.enabled:
            # Disable old, enable new
            self._set_generator_telemetry_rate(self.target_slot, 0)
            self.target_slot = slot
            self._set_generator_telemetry_rate(slot, self.current_rate)
            self.history.clear()
    
    def _set_generator_telemetry_rate(self, slot: int, rate: int):
        """Send OSC to set telemetryRate on generator synth."""
        if self.sc_client is None:
            return
        
        # This assumes the generator synth is accessible via /n_set
        # Actual implementation depends on your SC client and node tracking
        try:
            # Pattern: /n_set <nodeID> telemetryRate <rate>
            # You'll need to track generator node IDs in your slot infrastructure
            self.sc_client.send('/telem/enable', [slot, rate])
        except Exception as e:
            print(f"[Telemetry] Failed to set rate: {e}")
    
    def _handle_telemetry(self, address, *args):
        """
        Process incoming /telem/gen message.
        
        Expected args: [slot, freq, phase, p0, p1, p2, p3, p4, 
                        rms1, rms2, rms3, peak, badValue]
        """
        if len(args) < 12:
            print(f"[Telemetry] Malformed message: {len(args)} args")
            return
        
        slot = int(args[0])
        if slot != self.target_slot:
            return
        
        data = {
            'slot': slot,
            'freq': float(args[1]),
            'phase': float(args[2]),
            'p0': float(args[3]),
            'p1': float(args[4]),
            'p2': float(args[5]),
            'p3': float(args[6]),
            'p4': float(args[7]),
            'rms_stage1': float(args[8]),
            'rms_stage2': float(args[9]),
            'rms_stage3': float(args[10]),
            'peak': float(args[11]),
            'bad_value': int(args[12]) if len(args) > 12 else 0,
            'timestamp': time.time()
        }
        
        # History management
        self.history.append(data)
        if len(self.history) > self.history_max:
            self.history.pop(0)
        
        # Check for bad values
        if data['bad_value'] > 0:
            error_type = "NaN" if data['bad_value'] == 1 else "∞"
            self.core_lock.emit(slot, error_type)
        
        self.data_received.emit(slot, data)
    
    def _handle_waveform(self, address, *args):
        """
        Process incoming /telem/wave message.
        
        Expected args: [slot, ...samples (128 floats)]
        """
        if len(args) < 2:
            return
        
        slot = int(args[0])
        if slot != self.target_slot:
            return
        
        samples = np.array(args[1:], dtype=np.float32)
        self.current_waveform = samples
        self.waveform_received.emit(slot, samples)
    
    def get_latest(self) -> Optional[Dict]:
        """Get most recent telemetry frame."""
        return self.history[-1] if self.history else None
    
    def get_git_hash(self) -> str:
        """Get current git hash for provenance tracking."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--short', 'HEAD'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except Exception:
            return "unknown"
    
    def snapshot(self) -> Optional[Dict]:
        """
        Capture current state for logging/export.
        
        Returns:
            Dict with frame data and provenance, or None if no data
        """
        if not self.history:
            return None
        
        return {
            'frame': self.history[-1].copy(),
            'waveform': self.current_waveform.tolist() if self.current_waveform is not None else None,
            'history_length': len(self.history),
            'captured_at': datetime.now().isoformat(),
            'provenance': {
                'generator_id': self.current_generator_id,
                'synthdef': self.current_synthdef_name,
                'git_hash': self.get_git_hash(),
                'noise_engine_version': self.app_version,
                'slot': self.target_slot,
                'telemetry_rate': self.current_rate
            }
        }
    
    def export_history(self, path: str):
        """Export full telemetry history to JSON."""
        data = {
            'history': self.history,
            'provenance': {
                'generator_id': self.current_generator_id,
                'synthdef': self.current_synthdef_name,
                'git_hash': self.get_git_hash(),
                'exported_at': datetime.now().isoformat()
            }
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"[Telemetry] Exported {len(self.history)} frames to {path}")


# =============================================================================
# OVERLAY RENDERER (PyQtGraph)
# =============================================================================

if HAS_PYQTGRAPH:
    class OverlayRenderer:
        """
        Renders ideal vs actual waveform comparison with phase alignment.
        Integrates with existing ScopeWidget.
        """
        
        # Waveform types
        TYPES = ['sine', 'square', 'saw', 'triangle', 'folded_sine', 'b258_morph']
        
        def __init__(self, plot_widget: pg.PlotWidget):
            self.plot = plot_widget
            self.ideal_gen = IdealOverlay(128)
            
            # Actual waveform trace (phosphor green)
            self.actual_trace = self.plot.plot(
                pen=pg.mkPen('#00ff88', width=2),
                name='Actual'
            )
            
            # Ideal waveform trace (orange dashed)
            self.ideal_trace = self.plot.plot(
                pen=pg.mkPen('#ff8800', width=1, style=Qt.DashLine),
                name='Ideal'
            )
            
            # Difference trace (optional, red)
            self.diff_trace = self.plot.plot(
                pen=pg.mkPen('#ff0044', width=1),
                name='Diff'
            )
            self.diff_trace.hide()
            
            # Current ideal settings
            self.ideal_type = 'sine'
            self.show_ideal = True
            self.show_diff = False
        
        def set_ideal_type(self, waveform_type: str):
            """Set which ideal waveform to overlay."""
            if waveform_type in self.TYPES:
                self.ideal_type = waveform_type
        
        def set_show_ideal(self, show: bool):
            """Toggle ideal overlay visibility."""
            self.show_ideal = show
            if show:
                self.ideal_trace.show()
            else:
                self.ideal_trace.hide()
        
        def set_show_diff(self, show: bool):
            """Toggle difference trace visibility."""
            self.show_diff = show
            if show:
                self.diff_trace.show()
            else:
                self.diff_trace.hide()
        
        def update(
            self, 
            actual_samples: np.ndarray, 
            phase: float, 
            params: Dict
        ):
            """
            Update display with phase-aligned actual and ideal waveforms.
            
            Args:
                actual_samples: Raw waveform from /telem/wave
                phase: Current oscillator phase (0-1) from /telem/gen
                params: Current P0-P4 values for ideal waveform generation
            """
            # Generate ideal based on current type and params
            ideal = self._generate_ideal(params)
            
            # Phase-align ideal to match actual
            ideal_aligned = self.ideal_gen.align_to_phase(ideal, phase)
            
            # Resample if lengths differ
            if len(ideal_aligned) != len(actual_samples):
                ideal_aligned = np.interp(
                    np.linspace(0, 1, len(actual_samples)),
                    np.linspace(0, 1, len(ideal_aligned)),
                    ideal_aligned
                )
            
            # Update traces
            x = np.arange(len(actual_samples))
            self.actual_trace.setData(x, actual_samples)
            
            if self.show_ideal:
                self.ideal_trace.setData(x, ideal_aligned)
            
            if self.show_diff:
                diff = actual_samples - ideal_aligned
                self.diff_trace.setData(x, diff)
        
        def _generate_ideal(self, params: Dict) -> np.ndarray:
            """Generate ideal waveform based on current type and params."""
            if self.ideal_type == 'sine':
                return self.ideal_gen.ideal_sine()
            
            elif self.ideal_type == 'square':
                return self.ideal_gen.ideal_square()
            
            elif self.ideal_type == 'saw':
                return self.ideal_gen.ideal_saw()
            
            elif self.ideal_type == 'triangle':
                return self.ideal_gen.ideal_triangle()
            
            elif self.ideal_type == 'folded_sine':
                fold = params.get('p1', 0.5)
                return self.ideal_gen.ideal_folded_sine(fold)
            
            elif self.ideal_type == 'b258_morph':
                return self.ideal_gen.ideal_b258_morph(
                    shape=params.get('p1', 0),
                    fold=params.get('p0', 0.5),
                    sym=params.get('p3', 0.5) - 0.5,
                    drive=params.get('p4', 0.5)
                )
            
            return self.ideal_gen.ideal_sine()


# =============================================================================
# VERTICAL METER WIDGET
# =============================================================================

class VerticalMeter(QFrame):
    """Simple vertical level meter for stage RMS display."""
    
    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self.label_text = label
        self.value = 0.0
        
        self.setMinimumWidth(30)
        self.setMinimumHeight(100)
        self.setFrameStyle(QFrame.Box | QFrame.Sunken)
        self.setStyleSheet("background: #1a1a1a; border: 1px solid #333;")
    
    def setValue(self, value: float):
        """Set meter value (0-1 linear, displayed as dB)."""
        self.value = max(0.0, min(1.0, value))
        self.update()
    
    def paintEvent(self, event):
        super().paintEvent(event)
        from PyQt5.QtGui import QPainter, QColor, QLinearGradient
        
        painter = QPainter(self)
        rect = self.rect().adjusted(2, 2, -2, -2)
        
        # Background
        painter.fillRect(rect, QColor('#0a0a0a'))
        
        # Meter fill
        if self.value > 0:
            # dB scaling: -60dB to 0dB
            db = 20 * np.log10(max(self.value, 1e-6))
            normalized = (db + 60) / 60  # 0 at -60dB, 1 at 0dB
            normalized = max(0, min(1, normalized))
            
            fill_height = int(rect.height() * normalized)
            fill_rect = rect.adjusted(0, rect.height() - fill_height, 0, 0)
            
            # Gradient: green -> yellow -> red
            gradient = QLinearGradient(0, rect.bottom(), 0, rect.top())
            gradient.setColorAt(0.0, QColor('#00ff88'))
            gradient.setColorAt(0.7, QColor('#ffff00'))
            gradient.setColorAt(1.0, QColor('#ff4444'))
            
            painter.fillRect(fill_rect, gradient)
        
        # Label
        painter.setPen(QColor('#888888'))
        painter.drawText(rect, Qt.AlignBottom | Qt.AlignHCenter, self.label_text)
        
        painter.end()


# =============================================================================
# TELEMETRY WIDGET
# =============================================================================

class TelemetryWidget(QWidget):
    """
    Development tool displaying real-time generator telemetry.
    
    Features:
    - Slot selection and enable/disable
    - P0-P4 parameter display
    - Stage RMS meters
    - Peak indicator with color coding
    - Core Lock warning for NaN/inf
    - Auto-snapshot functionality
    """
    
    def __init__(self, controller: TelemetryController, parent=None):
        super().__init__(parent)
        self.controller = controller
        
        # Connect signals
        self.controller.data_received.connect(self._update_display)
        self.controller.core_lock.connect(self._show_core_lock)
        
        self._setup_ui()
        
        # Auto-disable on close
        self.setAttribute(Qt.WA_DeleteOnClose)
    
    def _setup_ui(self):
        self.setWindowTitle("DSP Telemetry")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # Header: Slot selector + enable toggle
        header = QHBoxLayout()
        
        self.slot_combo = QComboBox()
        self.slot_combo.addItems([f"Slot {i+1}" for i in range(8)])
        self.slot_combo.currentIndexChanged.connect(self._slot_changed)
        
        self.enable_btn = QPushButton("Enable")
        self.enable_btn.setCheckable(True)
        self.enable_btn.setStyleSheet("""
            QPushButton { background: #333; color: #888; padding: 6px 12px; }
            QPushButton:checked { background: #00aa44; color: white; }
        """)
        self.enable_btn.toggled.connect(self._toggle_telemetry)
        
        header.addWidget(QLabel("Monitor:"))
        header.addWidget(self.slot_combo)
        header.addStretch()
        header.addWidget(self.enable_btn)
        layout.addLayout(header)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #333;")
        layout.addWidget(line)
        
        # Parameter display
        param_frame = QFrame()
        param_frame.setStyleSheet("background: #1a1a1a; padding: 4px;")
        param_grid = QGridLayout(param_frame)
        param_grid.setSpacing(4)
        
        self.param_labels = {}
        param_names = ['FRQ', 'P0', 'P1', 'P2', 'P3', 'P4']
        
        for i, name in enumerate(param_names):
            label = QLabel(name)
            label.setStyleSheet("color: #888; font-size: 11px;")
            
            value = QLabel("---")
            value.setStyleSheet("""
                color: #00ff88; 
                font-family: 'JetBrains Mono', 'Consolas', monospace; 
                font-size: 14px;
            """)
            value.setAlignment(Qt.AlignCenter)
            
            param_grid.addWidget(label, 0, i, Qt.AlignCenter)
            param_grid.addWidget(value, 1, i, Qt.AlignCenter)
            self.param_labels[name] = value
        
        layout.addWidget(param_frame)
        
        # Stage meters
        meter_layout = QHBoxLayout()
        meter_layout.addStretch()
        
        self.stage_meters = []
        for name in ['S1', 'S2', 'S3']:
            meter = VerticalMeter(name)
            self.stage_meters.append(meter)
            meter_layout.addWidget(meter)
        
        meter_layout.addStretch()
        layout.addLayout(meter_layout)
        
        # Peak indicator
        self.peak_label = QLabel("Peak: ---")
        self.peak_label.setAlignment(Qt.AlignCenter)
        self.peak_label.setStyleSheet("""
            font-size: 18px; 
            font-weight: bold; 
            color: #00ff88;
            padding: 8px;
        """)
        layout.addWidget(self.peak_label)
        
        # Core Lock warning (hidden by default)
        self.core_lock_label = QLabel()
        self.core_lock_label.setAlignment(Qt.AlignCenter)
        self.core_lock_label.setStyleSheet("""
            background: red; 
            color: white; 
            padding: 8px; 
            font-weight: bold;
            font-size: 14px;
        """)
        self.core_lock_label.hide()
        layout.addWidget(self.core_lock_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.snapshot_btn = QPushButton("📸 Snapshot")
        self.snapshot_btn.clicked.connect(self._take_snapshot)
        self.snapshot_btn.setToolTip("Save current telemetry to JSON (Ctrl+S)")
        
        self.export_btn = QPushButton("📁 Export History")
        self.export_btn.clicked.connect(self._export_history)
        
        btn_layout.addWidget(self.snapshot_btn)
        btn_layout.addWidget(self.export_btn)
        layout.addLayout(btn_layout)
        
        # Status bar
        self.status_label = QLabel("Telemetry disabled")
        self.status_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.status_label)
    
    def _slot_changed(self, index: int):
        """Handle slot selection change."""
        if self.controller.enabled:
            self.controller.set_slot(index)
    
    def _toggle_telemetry(self, enabled: bool):
        """Toggle telemetry on/off."""
        slot = self.slot_combo.currentIndex()
        
        if enabled:
            self.controller.enable(slot, rate=15)
            self.enable_btn.setText("Disable")
            self.status_label.setText(f"Monitoring slot {slot + 1} at 15Hz")
        else:
            self.controller.disable()
            self.enable_btn.setText("Enable")
            self.status_label.setText("Telemetry disabled")
            self._clear_display()
    
    def _update_display(self, slot: int, data: dict):
        """Update UI with new telemetry data."""
        # Frequency
        self.param_labels['FRQ'].setText(f"{data['freq']:.1f}")
        
        # P0-P4
        for i in range(5):
            self.param_labels[f'P{i}'].setText(f"{data[f'p{i}']:.3f}")
        
        # Stage meters
        self.stage_meters[0].setValue(data['rms_stage1'])
        self.stage_meters[1].setValue(data['rms_stage2'])
        self.stage_meters[2].setValue(data['rms_stage3'])
        
        # Peak indicator
        peak = max(data['peak'], 1e-6)
        peak_db = 20 * np.log10(peak)
        self.peak_label.setText(f"Peak: {peak_db:.1f} dB")
        
        # Color code peak
        if peak_db > -3:
            color = "red"
        elif peak_db > -6:
            color = "orange"
        else:
            color = "#00ff88"
        
        self.peak_label.setStyleSheet(f"""
            font-size: 18px; 
            font-weight: bold; 
            color: {color};
            padding: 8px;
        """)
        
        # Clear core lock if value is clean
        if data.get('bad_value', 0) == 0:
            self.core_lock_label.hide()
    
    def _show_core_lock(self, slot: int, error_type: str):
        """Show core lock warning."""
        self.core_lock_label.setText(f"⚠️ CORE LOCK: {error_type}")
        self.core_lock_label.show()
    
    def _clear_display(self):
        """Clear all display values."""
        for label in self.param_labels.values():
            label.setText("---")
        for meter in self.stage_meters:
            meter.setValue(0)
        self.peak_label.setText("Peak: ---")
        self.core_lock_label.hide()
    
    def _take_snapshot(self):
        """Capture current telemetry to JSON file."""
        snapshot = self.controller.snapshot()
        if not snapshot:
            QMessageBox.warning(self, "Snapshot", "No telemetry data to capture")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"telemetry_snapshot_{timestamp}.json"
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Snapshot", default_name, "JSON Files (*.json)"
        )
        
        if path:
            with open(path, 'w') as f:
                json.dump(snapshot, f, indent=2)
            self.status_label.setText(f"Snapshot saved: {Path(path).name}")
    
    def _export_history(self):
        """Export full telemetry history."""
        if not self.controller.history:
            QMessageBox.warning(self, "Export", "No history to export")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"telemetry_history_{timestamp}.json"
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Export History", default_name, "JSON Files (*.json)"
        )
        
        if path:
            self.controller.export_history(path)
            self.status_label.setText(f"Exported {len(self.controller.history)} frames")
    
    def closeEvent(self, event):
        """Disable telemetry when window closes."""
        self.controller.disable()
        super().closeEvent(event)


# =============================================================================
# ENTRY POINT FOR TESTING
# =============================================================================

if __name__ == '__main__':
    """Test the telemetry widget with mock data."""
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Mock controller (no OSC connection)
    controller = TelemetryController(osc_server=None)
    
    # Create widget
    widget = TelemetryWidget(controller)
    widget.show()
    
    # Simulate incoming data
    def mock_data():
        import random
        data = {
            'slot': 0,
            'freq': 220.0 + random.random() * 10,
            'phase': random.random(),
            'p0': random.random(),
            'p1': random.random(),
            'p2': random.random(),
            'p3': random.random(),
            'p4': random.random(),
            'rms_stage1': 0.1 + random.random() * 0.2,
            'rms_stage2': 0.15 + random.random() * 0.3,
            'rms_stage3': 0.2 + random.random() * 0.4,
            'peak': 0.5 + random.random() * 0.4,
            'bad_value': 0,
            'timestamp': time.time()
        }
        controller.history.append(data)
        controller.data_received.emit(0, data)
    
    # Timer for mock data
    timer = QTimer()
    timer.timeout.connect(mock_data)
    timer.start(66)  # ~15fps
    
    # Enable display
    widget.enable_btn.setChecked(True)
    
    sys.exit(app.exec_())
