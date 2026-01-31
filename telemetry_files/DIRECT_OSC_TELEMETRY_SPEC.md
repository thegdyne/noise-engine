# DIRECT_OSC_TELEMETRY_SPEC.md — v0.1 (DRAFT)

*Real-Time DSP Telemetry for Generator Development*

---

## Status

|         |                   |
| ------- | ----------------- |
| Version | v0.1              |
| Status  | **DRAFT**         |
| Date    | 2026-01-31        |
| Author  | Gareth + Claude   |

---

## 1. Goal

Add a **Direct OSC Telemetry** system to Noise Engine that streams real-time DSP state from SuperCollider to Python, enabling:

1. **True Waveform Visualization** — See the raw waveshaper output before any hardware/driver filtering
2. **Parameter Correlation** — Visualize how P0-P4 values affect the waveform in real-time
3. **Ideal vs Actual Overlay** — Compare mathematical "ideal" shapes against actual DSP output
4. **Auto-Snapshot** — Capture parameter+waveform pairs for documentation and debugging

**Primary Use Case:** B258 wavefolder development, where subtle DSP changes (LeakDC placement, fold coefficients) cause visible waveform artifacts that are difficult to diagnose from audio alone.

---

## 2. Relationship to Existing Scope System

Noise Engine already has a **Scope Tap System** (`SCOPE_TAP_SPEC.md`) that:
- Captures audio from intermediate buses using ping-pong buffering
- Provides trigger-aligned display for stable waveform viewing
- Offers freeze functionality for analysis

**This spec is complementary, not a replacement.** The difference:

| System | What It Captures | When To Use |
|--------|------------------|-------------|
| **Scope Tap** | Raw audio samples from intermediate bus | General waveform monitoring, live performance |
| **OSC Telemetry** | DSP internal state + parameter values | Development debugging, generator tuning |

Telemetry is **development tooling** — it adds overhead and is not intended for live use. It can be disabled via a feature flag.

---

## 3. Architecture

### 3.1 Signal Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      GENERATOR SynthDef (with Telemetry)                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  p = In.kr(customBus0, 5);                                                  │
│  freq = In.kr(freqBus);                                                     │
│                                                                             │
│  // === DSP STAGES ===                                                      │
│  stage1 = SinOsc.ar(freq);           // Pure sine                          │
│  stage2 = (stage1 + sym).fold2(t);   // After fold                         │
│  stage3 = (stage2 * drive).tanh;     // After saturation                   │
│  sig = stage3;                                                              │
│                                                                             │
│  // === TELEMETRY TAP ===                                                   │
│  SendReply.kr(Impulse.kr(telemetryRate), '/telem/gen', [                   │
│      slotIndex,                       // Which slot                         │
│      freq,                            // Current frequency                  │
│      p[0], p[1], p[2], p[3], p[4],   // P0-P4 values                       │
│      Amplitude.ar(stage1),            // RMS of stage 1                    │
│      Amplitude.ar(stage2),            // RMS of stage 2                    │
│      Amplitude.ar(stage3),            // RMS of stage 3                    │
│      Peak.ar(sig, Impulse.kr(telemetryRate)).lag  // Peak output           │
│  ]);                                                                        │
│                                                                             │
│  sig = NumChannels.ar(sig, 2);                                              │
│  ReplaceOut.ar(out, sig);                                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ OSC: /telem/gen
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PYTHON TELEMETRY RECEIVER                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  TelemetryController:                                                       │
│    - Receives /telem/gen messages at ~15-30fps                             │
│    - Stores rolling buffer of parameter+metric pairs                        │
│    - Emits signals for UI update                                            │
│                                                                             │
│  TelemetryWidget:                                                           │
│    - Displays parameter values with real-time update                        │
│    - Shows stage RMS meters (stage1 → stage2 → stage3)                     │
│    - Peak indicator with hold                                               │
│    - Auto-snapshot button                                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Telemetry Message Format

```
OSC Path: /telem/gen
Arguments: [slotIndex, freq, phase, p0, p1, p2, p3, p4, rms1, rms2, rms3, peak, badValue]
Types:     [int,       float, float, float×5,              float×4,             int    ]
Rate:      15-30 Hz (configurable)
```

**Critical fields:**
- `phase` — Normalized 0-1 oscillator phase for Python phase-locking
- `badValue` — 1 if NaN/inf detected, 0 otherwise (CheckBadValues result)

### 3.3 Phase Alignment for Ideal Overlay

**The Problem:** `SendReply` and `SinOsc` are not sample-locked to Python's clock. If you draw an "ideal" sine over telemetry data without phase reference, they will drift — making it impossible to see if `LeakDC` is causing phase shift or if the fold topology is introducing asymmetry.

**The Solution:** Include normalized phase (0-1) in every telemetry message:

```supercollider
var phase = Phasor.ar(0, freq * SampleDur.ir, 0, 1);  // Normalized 0-1

SendReply.kr(Impulse.kr(telemetryRate), '/telem/gen', [
    slotIndex,
    freq,
    A2K.kr(phase),  // Phase at moment of SendReply
    // ... rest of params
]);
```

Python uses this to align the ideal waveform:

```python
def align_ideal_to_phase(ideal: np.ndarray, phase: float) -> np.ndarray:
    """Rotate ideal waveform to match current oscillator phase."""
    n = len(ideal)
    shift = int(phase * n)
    return np.roll(ideal, shift)
```

### 3.4 Extended Telemetry: Phase-Relative Waveform Capture

For detailed waveform analysis, an extended mode captures **exactly one cycle** of audio:

**The Problem:** Fixed sample counts (64-128) don't scale with frequency:
- At 44.1kHz, 128 samples = ~2.9ms
- At 60Hz, one cycle = ~16.7ms (128 samples captures only 17% of the cycle)
- At 5000Hz, one cycle = 0.2ms (128 samples captures 14+ cycles)

**The Solution:** Phase-relative sampling using `RecordBuf` triggered by zero-crossing:

```supercollider
// Capture exactly one cycle, regardless of frequency
var captureTrig = (phase < Delay1.ar(phase));  // Zero-crossing trigger
var capturePhase = Phasor.ar(captureTrig, 1, 0, BufFrames.kr(captureBuf));

BufWr.ar(sig, captureBuf, capturePhase);

// Burst buffer contents when capture complete
SendReply.ar(captureTrig, '/telem/wave', [slotIndex] ++ BufRd.ar(1, captureBuf, (0..127)));
```

```
OSC Path: /telem/wave  
Arguments: [slotIndex, ...samples (128 floats representing exactly 1 cycle)]
Rate:      Triggered by zero-crossing (frequency-dependent)
```

**Python receives one complete period** regardless of whether the generator is at 50Hz or 5000Hz, enabling accurate "Ideal vs Actual" comparison.

---

## 4. Generator Contract Extension

### 4.1 Telemetry-Enabled SynthDef Template

Generators that want telemetry support add a `telemetryRate` argument and `SendReply` block:

```supercollider
SynthDef(\forge_core_b258_dual_morph, { |out, freqBus, customBus0, telemetryRate=0|
    var sig, freq, p;
    var stage1, stage2, stage3;  // DSP stages for telemetry
    
    p = In.kr(customBus0, 5);
    freq = In.kr(freqBus).clip(5, 20000);
    
    // === DSP ===
    stage1 = SinOsc.ar(freq);
    stage2 = /* folding stage */;
    stage3 = /* saturation stage */;
    sig = stage3;
    
    // === TELEMETRY (only active when telemetryRate > 0) ===
    (telemetryRate > 0).if {
        SendReply.kr(Impulse.kr(telemetryRate), '/telem/gen', [
            \slotIndex.ir(0),
            freq,
            p[0], p[1], p[2], p[3], p[4],
            Amplitude.ar(stage1, 0.01, 0.1),
            Amplitude.ar(stage2, 0.01, 0.1),
            Amplitude.ar(stage3, 0.01, 0.1),
            Peak.ar(sig, Impulse.kr(telemetryRate)).lag(0.1)
        ]);
    };
    
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
```

### 4.2 Telemetry Contract Rules

| Rule | Requirement |
|------|-------------|
| `telemetryRate` argument | Default = 0 (disabled), range 0-60 Hz |
| Conditional SendReply | Only emit when telemetryRate > 0 |
| slotIndex passthrough | Receive via `\slotIndex.ir(0)` for message routing |
| Stage naming | Document which DSP stages are tapped in header comment |
| CPU budget | Max 3 Amplitude followers + 1 Peak per generator |

### 4.3 Existing Generators

Existing generators **do not require modification**. Telemetry is opt-in for development/debugging.

For generators under active development (like B258 variants), add telemetry temporarily during tuning, then optionally remove before release.

---

## 5. Python Components

### 5.1 TelemetryController

```python
class TelemetryController(QObject):
    """
    Receives and processes OSC telemetry from SuperCollider.
    """
    
    # Signals
    data_received = pyqtSignal(int, dict)  # slot, data dict
    
    def __init__(self, osc_server):
        super().__init__()
        self.osc_server = osc_server
        self.enabled = False
        self.target_slot = 0
        self.history = []  # Rolling buffer of recent frames
        self.history_max = 300  # ~10 seconds at 30fps
        
        # Register OSC handler
        osc_server.add_handler('/telem/gen', self._handle_telemetry)
        osc_server.add_handler('/telem/wave', self._handle_waveform)
    
    def enable(self, slot: int, rate: int = 15):
        """Enable telemetry for a specific slot."""
        self.target_slot = slot
        self.enabled = True
        # Send OSC to set telemetryRate on the generator synth
        self._set_generator_telemetry_rate(slot, rate)
    
    def disable(self):
        """Disable telemetry."""
        if self.enabled:
            self._set_generator_telemetry_rate(self.target_slot, 0)
        self.enabled = False
    
    def _handle_telemetry(self, address, *args):
        """Process incoming /telem/gen message."""
        slot = int(args[0])
        if slot != self.target_slot:
            return
        
        data = {
            'slot': slot,
            'freq': args[1],
            'phase': args[2],  # Normalized 0-1 for ideal overlay sync
            'p0': args[3], 'p1': args[4], 'p2': args[5], 
            'p3': args[6], 'p4': args[7],
            'rms_stage1': args[8],
            'rms_stage2': args[9],
            'rms_stage3': args[10],
            'peak': args[11],
            'bad_value': int(args[12]) if len(args) > 12 else 0,  # 0=clean, 1=NaN, 2=inf
            'timestamp': time.time()
        }
        
        self.history.append(data)
        if len(self.history) > self.history_max:
            self.history.pop(0)
        
        self.data_received.emit(slot, data)
    
    def _handle_waveform(self, address, *args):
        """Process incoming /telem/wave message (extended mode)."""
        slot = int(args[0])
        samples = np.array(args[1:], dtype=np.float32)
        # Emit for scope overlay
        self.waveform_received.emit(slot, samples)
    
    def snapshot(self) -> dict:
        """
        Capture current state for logging/export.
        
        Includes provenance data for reproducibility:
        - Generator ID and SynthDef name
        - Git hash of current codebase (if available)
        - Full parameter state
        """
        if not self.history:
            return None
        
        # Get git hash for provenance
        try:
            import subprocess
            git_hash = subprocess.check_output(
                ['git', 'rev-parse', '--short', 'HEAD'],
                cwd=self.project_root,
                stderr=subprocess.DEVNULL
            ).decode().strip()
        except:
            git_hash = "unknown"
        
        return {
            'frame': self.history[-1].copy(),
            'history_length': len(self.history),
            'captured_at': time.time(),
            'provenance': {
                'generator_id': self.current_generator_id,
                'synthdef': self.current_synthdef_name,
                'git_hash': git_hash,
                'noise_engine_version': self.app_version
            }
        }
    
    def export_history(self, path: str):
        """Export telemetry history to JSON."""
        import json
        with open(path, 'w') as f:
            json.dump(self.history, f, indent=2)
```

### 5.2 TelemetryWidget

```python
class TelemetryWidget(QWidget):
    """
    Development tool displaying real-time generator telemetry.
    """
    
    def __init__(self, controller: TelemetryController, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.controller.data_received.connect(self._update_display)
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header: Slot selector + enable toggle
        header = QHBoxLayout()
        self.slot_combo = QComboBox()
        self.slot_combo.addItems([f"Slot {i+1}" for i in range(8)])
        self.enable_btn = QPushButton("Enable Telemetry")
        self.enable_btn.setCheckable(True)
        self.enable_btn.toggled.connect(self._toggle_telemetry)
        header.addWidget(QLabel("Monitor:"))
        header.addWidget(self.slot_combo)
        header.addWidget(self.enable_btn)
        layout.addLayout(header)
        
        # Parameter display
        self.param_labels = {}
        param_grid = QGridLayout()
        for i, name in enumerate(['FRQ', 'P0', 'P1', 'P2', 'P3', 'P4']):
            label = QLabel(name)
            value = QLabel("---")
            value.setStyleSheet("font-family: monospace; font-size: 14px;")
            param_grid.addWidget(label, 0, i)
            param_grid.addWidget(value, 1, i)
            self.param_labels[name] = value
        layout.addLayout(param_grid)
        
        # Stage meters (RMS)
        self.stage_meters = []
        meter_layout = QHBoxLayout()
        for name in ['Stage 1', 'Stage 2', 'Stage 3']:
            meter = VerticalMeter(name)
            self.stage_meters.append(meter)
            meter_layout.addWidget(meter)
        layout.addLayout(meter_layout)
        
        # Peak indicator
        self.peak_label = QLabel("Peak: ---")
        self.peak_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(self.peak_label)
        
        # Snapshot button
        self.snapshot_btn = QPushButton("📸 Snapshot (Ctrl+S)")
        self.snapshot_btn.clicked.connect(self._take_snapshot)
        layout.addWidget(self.snapshot_btn)
    
    def _toggle_telemetry(self, enabled: bool):
        slot = self.slot_combo.currentIndex()
        if enabled:
            self.controller.enable(slot, rate=15)
            self.enable_btn.setText("Disable Telemetry")
        else:
            self.controller.disable()
            self.enable_btn.setText("Enable Telemetry")
    
    def _update_display(self, slot: int, data: dict):
        """Update UI with new telemetry data."""
        # Parameter values
        self.param_labels['FRQ'].setText(f"{data['freq']:.1f}")
        for i in range(5):
            self.param_labels[f'P{i}'].setText(f"{data[f'p{i}']:.3f}")
        
        # Stage meters
        self.stage_meters[0].setValue(data['rms_stage1'])
        self.stage_meters[1].setValue(data['rms_stage2'])
        self.stage_meters[2].setValue(data['rms_stage3'])
        
        # Peak indicator
        peak_db = 20 * np.log10(max(data['peak'], 1e-6))
        self.peak_label.setText(f"Peak: {peak_db:.1f} dB")
        
        # Color code peak
        if peak_db > -3:
            self.peak_label.setStyleSheet("color: red; font-size: 18px; font-weight: bold;")
        elif peak_db > -6:
            self.peak_label.setStyleSheet("color: orange; font-size: 18px; font-weight: bold;")
        else:
            self.peak_label.setStyleSheet("color: #00ff88; font-size: 18px; font-weight: bold;")
        
        # Bad value detection (CORE LOCK warning)
        bad_value = data.get('bad_value', 0)
        if bad_value > 0:
            warning_type = "NaN" if bad_value == 1 else "∞"
            self.core_lock_label.setText(f"⚠️ CORE LOCK: {warning_type}")
            self.core_lock_label.setStyleSheet(
                "background: red; color: white; padding: 4px; font-weight: bold;"
            )
            self.core_lock_label.show()
        else:
            self.core_lock_label.hide()
    
    def _take_snapshot(self):
        """Capture current telemetry + optional scope image."""
        snapshot = self.controller.snapshot()
        if snapshot:
            # Save to timestamped file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = f"telemetry_snapshot_{timestamp}.json"
            with open(path, 'w') as f:
                json.dump(snapshot, f, indent=2)
            print(f"[Telemetry] Snapshot saved to {path}")
```

### 5.3 Phase-Locked Ideal Overlay

For comparing actual DSP output against mathematical "ideal" shapes with proper phase alignment:

```python
class IdealOverlay:
    """
    Generates mathematical ideal waveforms for comparison.
    All methods return waveforms that can be phase-aligned to telemetry data.
    """
    
    def __init__(self, n_samples: int = 128):
        self.n_samples = n_samples
        self.t = np.linspace(0, 2*np.pi, n_samples, endpoint=False)
    
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
        return np.where(phase_norm < duty, 1.0, -1.0)
    
    def ideal_saw(self) -> np.ndarray:
        """Perfect sawtooth (ramp up, instant reset)."""
        return 2 * (self.t / (2 * np.pi)) - 1
    
    def ideal_triangle(self) -> np.ndarray:
        """Perfect triangle wave."""
        return 2 * np.abs(2 * (self.t / (2 * np.pi)) - 1) - 1
    
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
        if np.max(np.abs(sig)) > 0:
            sig = sig / np.max(np.abs(sig))
        
        return sig
    
    def ideal_b258_morph(self, shape: float, fold: float, sym: float = 0.0) -> np.ndarray:
        """
        Complete B258 dual-morph ideal waveform.
        
        Args:
            shape: 0.0 = sine, 0.5 = square-ish, 1.0 = saw
            fold: Fold intensity (0-1)
            sym: Symmetry offset (-0.5 to 0.5)
        
        Returns:
            Ideal waveform matching the B258 dual-morph topology
        """
        sine = np.sin(self.t)
        
        # Square path (tanh saturation)
        sqr_drive = 1 + (fold * 60 * (1 - shape))  # Reciprocal law
        sqr = np.tanh((sine + sym) * sqr_drive)
        
        # Saw path (fold)
        saw_blend = sine * (1 - shape) + self.ideal_saw() * shape
        saw = np.clip(saw_blend + sym, -0.9, 0.9)
        
        # Morph
        if shape < 0.5:
            # Sine to square
            t = shape * 2
            return sine * (1 - t) + sqr * t
        else:
            # Square to saw
            t = (shape - 0.5) * 2
            return sqr * (1 - t) + saw * t


class OverlayRenderer:
    """
    Renders ideal vs actual waveform comparison with phase alignment.
    """
    
    def __init__(self, plot_widget):
        self.plot = plot_widget
        self.ideal_generator = IdealOverlay(128)
        
        # Traces
        self.actual_trace = self.plot.plot(
            pen=pg.mkPen('#00ff88', width=2),  # Phosphor green
            name='Actual'
        )
        self.ideal_trace = self.plot.plot(
            pen=pg.mkPen('#ff8800', width=1, style=Qt.DashLine),  # Orange dashed
            name='Ideal'
        )
        
        # Current ideal waveform type
        self.ideal_type = 'sine'
        self.ideal_params = {}
    
    def set_ideal_type(self, waveform_type: str, **params):
        """Set which ideal waveform to overlay."""
        self.ideal_type = waveform_type
        self.ideal_params = params
    
    def update(self, actual_samples: np.ndarray, phase: float, params: dict):
        """
        Update display with phase-aligned actual and ideal waveforms.
        
        Args:
            actual_samples: Raw waveform from /telem/wave
            phase: Current oscillator phase (0-1) from /telem/gen
            params: Current P0-P4 values for ideal waveform generation
        """
        # Generate ideal based on current type
        if self.ideal_type == 'sine':
            ideal = self.ideal_generator.ideal_sine()
        elif self.ideal_type == 'square':
            ideal = self.ideal_generator.ideal_square()
        elif self.ideal_type == 'saw':
            ideal = self.ideal_generator.ideal_saw()
        elif self.ideal_type == 'folded_sine':
            fold = params.get('p1', 0.5)  # P1 = fold in B258
            ideal = self.ideal_generator.ideal_folded_sine(fold)
        elif self.ideal_type == 'b258_morph':
            ideal = self.ideal_generator.ideal_b258_morph(
                shape=params.get('p1', 0),
                fold=params.get('p0', 0.5),
                sym=params.get('p3', 0) - 0.5  # Normalize to -0.5..0.5
            )
        else:
            ideal = self.ideal_generator.ideal_sine()
        
        # Phase-align ideal to match actual
        ideal_aligned = self.ideal_generator.align_to_phase(ideal, phase)
        
        # Update traces
        x = np.arange(len(actual_samples))
        self.actual_trace.setData(x, actual_samples)
        
        # Resample ideal if lengths differ
        if len(ideal_aligned) != len(actual_samples):
            ideal_aligned = np.interp(
                np.linspace(0, 1, len(actual_samples)),
                np.linspace(0, 1, len(ideal_aligned)),
                ideal_aligned
            )
        self.ideal_trace.setData(x, ideal_aligned)
```

---

## 6. UI Integration

### 6.1 Access Point

Telemetry widget is accessible via:
- **Menu:** `Debug > Telemetry Monitor`
- **Keyboard:** `Ctrl+Shift+T`
- **Context Menu:** Right-click on generator slot header

### 6.2 Window Behavior

- **Floating window** (not docked)
- **Always on top** option
- **Remembers position** between sessions
- **Auto-disable** when window closes (saves CPU)

### 6.3 Integration with Existing Scope

When both Telemetry and Scope are active on the same slot:
- Telemetry provides parameter overlay on scope display
- Scope provides waveform, telemetry provides context
- "Ideal overlay" toggle shows mathematical comparison

---

## 7. Performance Considerations

### 7.1 CPU Budget

| Component | Overhead | Notes |
|-----------|----------|-------|
| SendReply.kr @ 15Hz | ~0.1% per generator | Minimal |
| Amplitude.ar followers | ~0.2% per follower | Max 3 per generator |
| Peak.ar | ~0.05% | Single instance |
| Phasor.ar (phase tracking) | ~0.02% | Negligible |
| CheckBadValues.ar | ~0.05% | Essential for stability |
| Python OSC handling | Negligible | Async processing |

**Total overhead when enabled:** ~0.6% CPU per monitored slot

### 7.2 Bad Value Detection (The Observer Effect)

Standard `Amplitude.ar` and `Peak.ar` don't catch **aliasing** or **inter-sample peaks** — critical failure modes for "Extreme" generators like B258 with high fold counts.

**Required:** Add `CheckBadValues` to telemetry:

```supercollider
var badValue = CheckBadValues.ar(sig, post: 0);  // 0 = don't post to console

SendReply.kr(Impulse.kr(telemetryRate), '/telem/gen', [
    // ... other params ...
    badValue  // 0 = clean, 1 = NaN, 2 = inf
]);
```

**Python response:**
```python
def _update_display(self, slot: int, data: dict):
    if data.get('bad_value', 0) > 0:
        self._flash_warning("⚠️ CORE LOCK: DSP produced NaN/inf!")
        self.core_lock_label.setStyleSheet("background: red; color: white;")
```

This provides immediate feedback when wavefolder parameters are pushed into unstable territory.

### 7.2 Disable by Default

Telemetry is **development tooling**, not production feature:
- `telemetryRate` defaults to 0 (no SendReply traffic)
- Only enabled when TelemetryWidget is open
- Auto-disables when widget closes

### 7.3 OSC Traffic

At 15 Hz with 11 float values per message:
- **44 bytes/message** × 15/sec = **660 bytes/sec** per slot
- Well within localhost UDP capacity

---

## 8. Implementation Phases

### Phase 1: Core Infrastructure (Session 1)

**Deliverables:**
- [ ] `TelemetryController` class with OSC handling
- [ ] Basic `TelemetryWidget` with parameter display
- [ ] OSC path registration in Python
- [ ] Test with mock OSC messages

**Verification:**
```bash
# Send test OSC message
python -c "from pythonosc import udp_client; c = udp_client.SimpleUDPClient('127.0.0.1', 57120); c.send_message('/telem/gen', [0, 440.0, 0.5, 0.3, 0.5, 0.5, 0.2, 0.1, 0.15, 0.12, 0.8])"
```

### Phase 2: Generator Integration (Session 2)

**Deliverables:**
- [ ] Update `forge_core_b258_dual_morph` with telemetry support
- [ ] Add `telemetryRate` argument to generator contract
- [ ] Test real SC → Python data flow
- [ ] Stage RMS meters working

**Verification:**
```bash
# Load generator, enable telemetry, verify OSC traffic
sclang -e "Synth('forge_core_b258_dual_morph', ['telemetryRate', 15])"
```

### Phase 3: Extended Features (Session 3)

**Deliverables:**
- [ ] Waveform telemetry (`/telem/wave`)
- [ ] Ideal overlay comparison
- [ ] Auto-snapshot functionality
- [ ] JSON export of history

### Phase 4: Polish (Session 4)

**Deliverables:**
- [ ] Kassutronics-style visual polish
- [ ] Keyboard shortcuts
- [ ] Integration with existing scope
- [ ] Documentation

---

## 9. Example: B258 Dual Morph with Telemetry

Based on AI2's phase-sync recommendations and the corrected DSP:

```supercollider
SynthDef(\forge_core_b258_dual_morph, { |out, freqBus, customBus0, telemetryRate=0|
    var sig, freq, p, sine, drive, shape, morph, sym, sat;
    var sqrPart, sawPart;
    var stage1, stage2, stage3;  // Telemetry taps
    var phase, badValue;         // Phase tracking + safety
    
    p = In.kr(customBus0, 5);
    
    // Smoothing to prevent "zipper" noise
    drive = Lag.kr(p[0], 0.05);
    shape = Lag.kr(p[1], 0.05);
    morph = Lag.kr(p[2], 0.05);
    sym   = Lag.kr(p[3].linlin(0, 1, -0.5, 0.5), 0.06);
    sat   = Lag.kr(p[4], 0.08);
    
    freq = In.kr(freqBus).clip(5, 20000);
    
    // Phase tracking for Python sync
    phase = Phasor.ar(0, freq * SampleDur.ir, 0, 1);
    
    // 1. THE SEED: High-precision Sine
    sine = SinOsc.ar(freq, 0);
    stage1 = sine;  // TAP: Pure input
    
    // 2. THE SQUARE PATH: Tanh-driven
    sqrPart = (sine + sym) * drive.linexp(0, 1, 1, 60);
    sqrPart = sqrPart.tanh;
    
    // 3. THE SAW PATH: 258 "Node" Folding
    sawPart = (sine * (1 - shape)) + (LFSaw.ar(freq, 1) * shape);
    sawPart = (sawPart + sym).fold2(0.9);
    stage2 = sawPart;  // TAP: After fold
    
    // 4. UNIFIED MORPH
    sig = SelectX.ar(morph * 2, [sine, sqrPart, sawPart]);
    
    // 5. POST-PROCESSING
    sig = (sig * sat.linexp(0, 1, 1, 12)).softclip;
    
    // CRITICAL: LeakDC at the very end with high coefficient
    sig = LeakDC.ar(sig, 0.995);
    stage3 = sig;  // TAP: Final output
    
    // Bad value detection (catches NaN/inf from extreme fold settings)
    badValue = CheckBadValues.ar(sig, post: 0);
    
    // === TELEMETRY (Phase-Locked) ===
    (telemetryRate > 0).if {
        SendReply.kr(Impulse.kr(telemetryRate), '/telem/gen', [
            \slotIndex.ir(0),
            freq,
            A2K.kr(phase),  // Normalized 0-1 phase for Python sync
            p[0], p[1], p[2], p[3], p[4],
            Amplitude.ar(stage1, 0.01, 0.1),
            Amplitude.ar(stage2, 0.01, 0.1),
            Amplitude.ar(stage3, 0.01, 0.1),
            Peak.ar(sig, Impulse.kr(telemetryRate)).lag(0.1),
            A2K.kr(badValue)  // 0=clean, 1=NaN, 2=inf
        ]);
    };
    
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig * 0.75);
}).add;
```

---

## 10. Success Criteria

### Core Functionality
- [ ] TelemetryWidget displays live P0-P4 values at 15fps
- [ ] Stage RMS meters show signal flow through DSP stages
- [ ] Peak indicator with color coding (green/orange/red)
- [ ] Telemetry disabled by default (no CPU overhead)

### Phase-Locking (AI2 Review)
- [ ] **Phase Lock:** Python "Ideal" overlay stays stationary relative to incoming telemetry wave
- [ ] **Frequency-Agnostic Scaling:** Waveform capture shows exactly 1 full cycle whether at 50Hz or 5000Hz
- [ ] Phase drift < 1% over 10 seconds of monitoring

### Safety & Stability (AI2 Review)
- [ ] **Bad Value Detection:** UI flashes "⚠️ CORE LOCK" warning if DSP produces NaN or infinity
- [ ] CheckBadValues tap active on all telemetry-enabled generators
- [ ] No false positives during normal parameter sweeps

### Snapshot & Provenance
- [ ] Auto-snapshot saves JSON with parameter values
- [ ] Snapshot includes generator_id, synthdef name, git hash
- [ ] Snapshots loadable for A/B comparison

### Integration
- [ ] Works with B258 Dual Morph generator
- [ ] Integration with existing scope for overlay visualization
- [ ] Keyboard shortcut (Ctrl+Shift+T) opens telemetry window

---

## 11. Open Questions

| Question | Options | Notes |
|----------|---------|-------|
| Telemetry rate control | Fixed 15Hz vs user-adjustable | 15Hz is sufficient for debugging |
| Waveform telemetry sample count | 64 vs 128 samples | 128 better for fold visualization |
| Store in preset? | Yes vs No | No — development tool only |
| Global kill switch | Menu toggle vs always-conditional | Menu toggle cleaner |

---

## 12. References

- `SCOPE_TAP_SPEC.md` — Existing audio scope system
- `END_STAGE_ARCHITECTURE_SPEC.md` — Bus topology
- `HOWTO_CREATE_GENERATOR.md` — Generator contract
- SuperCollider `SendReply` documentation

---

**v0.1 — DRAFT**

*Ready for review. Key decision: Should waveform telemetry use a separate OSC path or extend the main telemetry message?*
