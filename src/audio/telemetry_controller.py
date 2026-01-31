"""
Telemetry Controller
Receives and processes OSC telemetry from SuperCollider.

Development-only tool for real-time DSP debugging of generators.
Data flows: SC SendReply → OSC bridge signal → this controller → widget.

Waveform data flows separately via telem_waveform_received signal.

References:
    telemetry_files/DIRECT_OSC_TELEMETRY_SPEC.md
    src/audio/scope_controller.py (pattern reference)
"""

import json
import subprocess
import time
from collections import deque
from datetime import datetime
from pathlib import Path

import numpy as np
from PyQt5.QtCore import QObject

from src.utils.logger import logger


# =============================================================================
# IDEAL WAVEFORM GENERATOR
# =============================================================================

class IdealOverlay:
    """
    Generates mathematical ideal waveforms matching the B258 Dual Morph
    SynthDef topology for phase-aligned comparison with live telemetry.

    The B258 SynthDef (b258_dual_morph.scd) has this signal flow:

        sine = SinOsc.ar(freq)

        Branch A (Square):
            sqr = (sine + sym) * linexp(p0, 0,1, 1,120)
            sqr = clip2(sqr, 1.0)

        Branch B (Saw):
            saw = sine * (1 - p1) + LFSaw(freq, iphase=1) * p1
            saw = clip2(saw + sym*0.5, 1.0)

        Mix:
            sig = XFade2(sqr, saw, linlin(p2, 0,1, -1,1))

        Saturation:
            sig = tanh(sig * linexp(p4, 0,1, 1,18))

        Output (single DC block):
            sig = LeakDC(sig, 0.995) * 0.8

    All methods operate on a single normalized cycle (0 to 2*pi).
    Phase alignment uses the normalized 0-1 phase from SC's Phasor.ar.
    """

    def __init__(self, n_samples: int = 128):
        self.n_samples = n_samples
        # One full cycle: 0 to 2*pi (endpoint=False for clean tiling)
        self.t = np.linspace(0, 2 * np.pi, n_samples, endpoint=False)
        # Normalized phase 0-1 for LFSaw calculation
        self.t_norm = np.linspace(0, 1, n_samples, endpoint=False)

    # -----------------------------------------------------------------
    # Phase alignment
    # -----------------------------------------------------------------

    def align_to_phase(self, waveform: np.ndarray, phase: float) -> np.ndarray:
        """
        Rotate waveform to match current oscillator phase from telemetry.

        Args:
            waveform: Ideal waveform array (one cycle)
            phase: Normalized 0-1 phase from SC Phasor.ar via A2K.kr

        Returns:
            Phase-aligned waveform (same length)
        """
        n = len(waveform)
        shift = int(phase * n)
        return np.roll(waveform, -shift)

    # -----------------------------------------------------------------
    # Primitive waveforms
    # -----------------------------------------------------------------

    def ideal_sine(self) -> np.ndarray:
        """Pure sine wave. Phase 0 = zero-crossing rising."""
        return np.sin(self.t).astype(np.float32)

    def ideal_saw_sc(self) -> np.ndarray:
        """
        LFSaw.ar(freq, iphase=1) equivalent.

        SC LFSaw with iphase=1 starts at 0, ramps to +1, wraps to -1,
        ramps back to 0 over one period. This is a standard bipolar saw
        offset by half a cycle.
        """
        # LFSaw(iphase=0): ramps -1 to +1 over one period
        # iphase=1 shifts by half a cycle: start at 0
        return (2 * ((self.t_norm + 0.5) % 1.0) - 1).astype(np.float32)

    # -----------------------------------------------------------------
    # SC DSP helper equivalents
    # -----------------------------------------------------------------

    @staticmethod
    def _linexp(val, in_min, in_max, out_min, out_max):
        """
        SC linexp: linear-to-exponential mapping.

        Maps val from [in_min, in_max] linearly to [out_min, out_max]
        exponentially: out_min * (out_max/out_min) ^ normalized_val
        """
        # Clamp to input range
        val = np.clip(val, in_min, in_max)
        normalized = (val - in_min) / (in_max - in_min)
        return out_min * (out_max / out_min) ** normalized

    @staticmethod
    def _linlin(val, in_min, in_max, out_min, out_max):
        """SC linlin: linear-to-linear mapping."""
        val = np.clip(val, in_min, in_max)
        normalized = (val - in_min) / (in_max - in_min)
        return out_min + normalized * (out_max - out_min)

    @staticmethod
    def _clip2(sig, threshold):
        """SC clip2: symmetric hard clip to +/- threshold."""
        return np.clip(sig, -threshold, threshold)

    @staticmethod
    def _leak_dc(sig, coeff=0.995):
        """
        SC LeakDC: first-order DC-blocking high-pass filter.

        Difference equation: y[n] = x[n] - x[n-1] + coeff * y[n-1]

        For single-cycle ideal waveforms, this mainly removes DC offset
        introduced by symmetry/bias operations. The coefficient 0.995
        matches SC's default.
        """
        out = np.zeros_like(sig)
        xm1 = 0.0
        ym1 = 0.0
        for i in range(len(sig)):
            out[i] = sig[i] - xm1 + coeff * ym1
            xm1 = sig[i]
            ym1 = out[i]
        return out

    @staticmethod
    def _xfade2(a, b, pan):
        """
        SC XFade2: equal-power crossfade.

        pan: -1 = all a, 0 = equal mix, +1 = all b
        Uses cosine/sine law for constant power.
        """
        pos_scaled = (pan + 1) * 0.25 * np.pi  # maps [-1,+1] to [0, pi/2]
        return a * np.cos(pos_scaled) + b * np.sin(pos_scaled)

    # -----------------------------------------------------------------
    # B258 Dual Morph — line-by-line match to SynthDef
    # -----------------------------------------------------------------

    def ideal_b258_dual_morph(
        self,
        p0_sine_sq: float,
        p1_sine_saw: float,
        p2_mix: float,
        p3_sym_raw: float,
        p4_sat: float,
    ) -> np.ndarray:
        """
        Generate ideal B258 Dual Morph waveform matching the SynthDef exactly.

        Args match the 5 custom params (0-1 range from GUI):
            p0_sine_sq:  Sine to Square morph amount
            p1_sine_saw: Sine to Saw morph amount
            p2_mix:      Balance between Square and Saw branches
            p3_sym_raw:  Symmetry (0-1 from GUI, mapped to -0.85..+0.85)
            p4_sat:      Final saturation amount

        Returns:
            float32 array of one cycle, matching SC output (pre-stereo)

        Each line below references the corresponding SynthDef line.
        """
        # --- PARAMETER MAPPING (b258_dual_morph.scd lines 30-34) ---
        # Lag.kr smoothing is irrelevant for ideal (steady-state)
        p3_sym = self._linlin(p3_sym_raw, 0, 1, -0.85, 0.85)

        # --- SINE SEED (line 40) ---
        sine = np.sin(self.t)

        # --- BRANCH A: SINE TO SQUARE (lines 54-57) ---
        # Drive = linexp(p0, 0, 1, 1, 120)
        sqr_drive = self._linexp(p0_sine_sq, 0, 1, 1, 120)
        sqr = (sine + p3_sym) * sqr_drive   # line 56
        sqr = self._clip2(sqr, 1.0)         # line 57

        # --- BRANCH B: SINE TO SAW (lines 59-62) ---
        # LFSaw.ar(freq, 1, p1_sineSaw) = LFSaw(iphase=1) * p1
        lf_saw = self.ideal_saw_sc()
        saw = (sine * (1 - p1_sine_saw)) + (lf_saw * p1_sine_saw)  # line 61
        saw = self._clip2(saw + (p3_sym * 0.5), 1.0)               # line 62

        # --- MIX (line 55) ---
        # XFade2.ar(sqr, saw, p2_mix.linlin(0, 1, -1, 1))
        pan = self._linlin(p2_mix, 0, 1, -1, 1)
        sig = self._xfade2(sqr, saw, pan)

        # --- FINAL SATURATION (line 58) ---
        # (sig * p4_sat.linexp(0, 1, 1, 18)).tanh
        sat_drive = self._linexp(p4_sat, 0, 1, 1, 18)
        sig = np.tanh(sig * sat_drive)

        # --- OUTPUT (line 72) — single DC block at end of chain ---
        sig = self._leak_dc(sig, 0.995) * 0.8

        return sig.astype(np.float32)

    # -----------------------------------------------------------------
    # Per-stage taps (for overlay comparison against stage RMS)
    # -----------------------------------------------------------------

    def ideal_b258_stages(
        self,
        p0_sine_sq: float,
        p1_sine_saw: float,
        p2_mix: float,
        p3_sym_raw: float,
        p4_sat: float,
    ) -> dict:
        """
        Return all three DSP stages separately for per-stage comparison.

        Returns dict with keys:
            'stage1': Pure sine seed (pre-shaping)
            'stage2': Post-morph XFade2 output (pre-saturation)
            'stage3': Final output (post-saturation, post-LeakDC)

        These correspond to the telemetry tap points in the SynthDef:
            stage1 = sine                    (line 40)
            stage2 = XFade2 output           (line 55)
            stage3 = LeakDC.ar(sig) * 0.8    (line 61)
        """
        p3_sym = self._linlin(p3_sym_raw, 0, 1, -0.85, 0.85)

        # Stage 1: sine seed
        sine = np.sin(self.t)
        stage1 = sine.copy()

        # Branch A
        sqr_drive = self._linexp(p0_sine_sq, 0, 1, 1, 120)
        sqr = (sine + p3_sym) * sqr_drive
        sqr = self._clip2(sqr, 1.0)

        # Branch B
        lf_saw = self.ideal_saw_sc()
        saw = (sine * (1 - p1_sine_saw)) + (lf_saw * p1_sine_saw)
        saw = self._clip2(saw + (p3_sym * 0.5), 1.0)

        # Stage 2: post-morph
        pan = self._linlin(p2_mix, 0, 1, -1, 1)
        stage2 = self._xfade2(sqr, saw, pan)

        # Stage 3: post-saturation + output (single DC block at end)
        sat_drive = self._linexp(p4_sat, 0, 1, 1, 18)
        sig = np.tanh(stage2 * sat_drive)
        stage3 = self._leak_dc(sig, 0.995) * 0.8

        return {
            'stage1': stage1.astype(np.float32),
            'stage2': stage2.astype(np.float32),
            'stage3': stage3.astype(np.float32),
        }

    # -----------------------------------------------------------------
    # Ideal RMS for each stage (for meter comparison)
    # -----------------------------------------------------------------

    def ideal_b258_rms(
        self,
        p0_sine_sq: float,
        p1_sine_saw: float,
        p2_mix: float,
        p3_sym_raw: float,
        p4_sat: float,
    ) -> dict:
        """
        Compute ideal RMS levels for each B258 stage.

        Returns dict with keys 'rms_stage1', 'rms_stage2', 'rms_stage3'.
        Values are linear amplitude (same scale as SC Amplitude.ar output).
        """
        stages = self.ideal_b258_stages(
            p0_sine_sq, p1_sine_saw, p2_mix, p3_sym_raw, p4_sat
        )
        return {
            'rms_stage1': float(np.sqrt(np.mean(stages['stage1'] ** 2))),
            'rms_stage2': float(np.sqrt(np.mean(stages['stage2'] ** 2))),
            'rms_stage3': float(np.sqrt(np.mean(stages['stage3'] ** 2))),
        }


# =============================================================================
# TELEMETRY CONTROLLER
# =============================================================================

class TelemetryController(QObject):
    """
    Manages telemetry communication with SuperCollider.

    Follows the ScopeController pattern:
    - Takes osc_bridge as constructor arg
    - Sends commands via self.osc.send() using OSC_PATHS keys
    - Receives data via on_data() / on_waveform() slots connected
      to OSCBridge signals by ConnectionController
    - Does NOT register its own OSC handlers

    Signals are emitted by OSCBridge, not this controller.
    """

    def __init__(self, osc_bridge):
        super().__init__()
        self.osc = osc_bridge

        # State
        self.enabled = False
        self.target_slot = 0
        self.current_rate = 15

        # History buffer (rolling)
        self.history = deque(maxlen=300)  # ~10 seconds at 30fps

        # Waveform buffer
        self.current_waveform = None

        # Generator info (set externally for snapshot provenance)
        self.current_generator_id = ""
        self.current_synthdef_name = ""
        self.app_version = ""

        # Ideal overlay generator
        self.ideal = IdealOverlay(128)

    # -----------------------------------------------------------------
    # Enable / disable
    # -----------------------------------------------------------------

    def enable(self, slot: int, rate: int = 15):
        """Enable telemetry for a specific slot.

        Args:
            slot: Generator slot index (0-7)
            rate: Update rate in Hz (5-60, default 15)
        """
        if not 0 <= slot < 8:
            logger.warning(f"[Telemetry] Invalid slot: {slot}")
            return

        rate = max(5, min(60, rate))
        self.target_slot = slot
        self.current_rate = rate
        self.enabled = True
        self.history.clear()

        # SC uses 1-based slots
        self.osc.send('telem_enable', [slot + 1, rate])
        logger.info(f"[Telemetry] Enabled for slot {slot} at {rate}Hz")

    def disable(self):
        """Disable telemetry."""
        if self.enabled:
            self.osc.send('telem_enable', [self.target_slot + 1, 0])
            self.enabled = False
            logger.info("[Telemetry] Disabled")

    def set_slot(self, slot: int):
        """Switch to monitoring a different slot."""
        if not 0 <= slot < 8:
            return
        if self.enabled:
            # Disable old slot, enable new
            self.osc.send('telem_enable', [self.target_slot + 1, 0])
            self.target_slot = slot
            self.osc.send('telem_enable', [slot + 1, self.current_rate])
            self.history.clear()
        else:
            self.target_slot = slot

    def enable_waveform(self, slot: int):
        """Enable waveform capture for a slot."""
        self.osc.send('telem_wave_enable', [slot + 1, 1])

    def disable_waveform(self, slot: int):
        """Disable waveform capture for a slot."""
        self.osc.send('telem_wave_enable', [slot + 1, 0])

    # -----------------------------------------------------------------
    # Data slots (connected to OSCBridge signals by ConnectionController)
    # -----------------------------------------------------------------

    def on_data(self, slot: int, data: dict):
        """Handle incoming telemetry data from OSCBridge signal.

        Called on Qt main thread (auto-queued from OSC thread).
        """
        if slot != self.target_slot:
            return

        data['timestamp'] = time.time()
        self.history.append(data)

    def on_waveform(self, slot: int, samples):
        """Handle incoming waveform data from OSCBridge signal."""
        if slot != self.target_slot:
            return

        self.current_waveform = np.asarray(samples, dtype=np.float32)

    # -----------------------------------------------------------------
    # Ideal overlay generation from current telemetry
    # -----------------------------------------------------------------

    def get_ideal_waveform(self, data: dict = None) -> np.ndarray:
        """Generate ideal B258 waveform from current or provided telemetry data.

        Returns phase-aligned ideal waveform array, or None if no data.
        """
        if data is None:
            data = self.get_latest()
        if data is None:
            return None

        ideal = self.ideal.ideal_b258_dual_morph(
            p0_sine_sq=data.get('p0', 0),
            p1_sine_saw=data.get('p1', 0),
            p2_mix=data.get('p2', 0.5),
            p3_sym_raw=data.get('p3', 0.5),
            p4_sat=data.get('p4', 0),
        )

        phase = data.get('phase', 0)
        return self.ideal.align_to_phase(ideal, phase)

    def get_ideal_rms(self, data: dict = None) -> dict:
        """Compute ideal RMS for each stage from current telemetry params."""
        if data is None:
            data = self.get_latest()
        if data is None:
            return None

        return self.ideal.ideal_b258_rms(
            p0_sine_sq=data.get('p0', 0),
            p1_sine_saw=data.get('p1', 0),
            p2_mix=data.get('p2', 0.5),
            p3_sym_raw=data.get('p3', 0.5),
            p4_sat=data.get('p4', 0),
        )

    # -----------------------------------------------------------------
    # Query
    # -----------------------------------------------------------------

    def get_latest(self):
        """Get most recent telemetry frame, or None."""
        return self.history[-1] if self.history else None

    # -----------------------------------------------------------------
    # Snapshot & export
    # -----------------------------------------------------------------

    def snapshot(self) -> dict:
        """Capture current state with provenance for reproducibility.

        Returns:
            Dict with frame, waveform, ideal, and provenance data.
            None if no telemetry data available.
        """
        if not self.history:
            return None

        latest = self.history[-1].copy()

        # Include ideal waveform for comparison
        ideal_wave = self.get_ideal_waveform(latest)
        ideal_rms = self.get_ideal_rms(latest)

        return {
            'frame': latest,
            'waveform': (
                self.current_waveform.tolist()
                if self.current_waveform is not None else None
            ),
            'ideal_waveform': (
                ideal_wave.tolist() if ideal_wave is not None else None
            ),
            'ideal_rms': ideal_rms,
            'history_length': len(self.history),
            'captured_at': datetime.now().isoformat(),
            'provenance': {
                'generator_id': self.current_generator_id,
                'synthdef': self.current_synthdef_name,
                'git_hash': self._get_git_hash(),
                'noise_engine_version': self.app_version,
                'slot': self.target_slot,
                'telemetry_rate': self.current_rate,
            }
        }

    def export_history(self, path: str):
        """Export full telemetry history to JSON."""
        data = {
            'history': list(self.history),
            'provenance': {
                'generator_id': self.current_generator_id,
                'synthdef': self.current_synthdef_name,
                'git_hash': self._get_git_hash(),
                'exported_at': datetime.now().isoformat(),
            }
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(
            f"[Telemetry] Exported {len(self.history)} frames to {path}"
        )

    def _get_git_hash(self) -> str:
        """Get current git hash for provenance tracking."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--short', 'HEAD'],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except Exception:
            return "unknown"
