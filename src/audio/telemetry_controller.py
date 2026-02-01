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
from scipy.optimize import minimize
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

        sine = SinOsc.ar(freq) * 0.8

        Branch A (Square):
            sqr = (sine + sym) * linexp(p0, 0,1, 1,120)
            sqr = clip2(sqr, 1.0)

        Branch B (Saw):
            saw = sine * (1 - p1) + LFSaw.ar(freq, 1) * p1
            saw = clip2(saw + sym*0.5, 1.0)

        Mix:
            sig = XFade2(sqr, saw, linlin(p2, 0,1, -1,1))

        Saturation:
            sig = tanh(sig * linexp(p4, 0,1, 1,18))

        Output (near-transparent DC block + normalized gain):
            sig = LeakDC(sig, 0.9999) * 0.66

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

        # --- SINE SEED (line 51) — calibrated amplitude ---
        sine = np.sin(self.t) * 0.8

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

        # --- OUTPUT (line 72) — near-transparent DC block + normalized gain ---
        sig = self._leak_dc(sig, 0.9999) * 0.66

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

        # Stage 1: sine seed (calibrated amplitude)
        sine = np.sin(self.t) * 0.8
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

        # Stage 3: post-saturation + output (near-transparent DC block + normalized gain)
        sat_drive = self._linexp(p4_sat, 0, 1, 1, 18)
        sig = np.tanh(stage2 * sat_drive)
        stage3 = self._leak_dc(sig, 0.9999) * 0.66

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

    Two-tier rate model:
    - MONITOR_RATE (5Hz): Light info-only mode for meters/params
    - CAPTURE_RATE (30Hz): Higher rate when waveform capture is active
    """

    MONITOR_RATE = 5    # Hz — info-only: meters, params, peak
    CAPTURE_RATE = 30   # Hz — active waveform capture mode

    # Hardware profiler detection
    HW_SYNTHDEF = 'forge_hw_profile_tap'
    HW_GENERATOR_NAME = 'Generic Hardware Profiler'
    HW_PARAM_LABELS = ['CHN', 'LVL', 'REF', 'SYM', 'SAT']
    DEFAULT_PARAM_LABELS = ['P0', 'P1', 'P2', 'P3', 'P4']

    # Capture types: determines waveform capture path
    CAPTURE_INTERNAL = 'internal'  # forge_telemetry_wave_capture synth reads ~intermediateBus
    CAPTURE_EXTERNAL = 'external'  # hw_profile_tap embeds its own capture (no action needed)

    def __init__(self, osc_bridge):
        super().__init__()
        self.osc = osc_bridge

        # State
        self.enabled = False
        self.waveform_active = False
        self.target_slot = 0
        self.current_rate = 0
        self._capture_type = self.CAPTURE_INTERNAL  # Set by set_generator_context()

        # History buffer (rolling)
        self.history = deque(maxlen=300)  # ~10 seconds at 30fps

        # Waveform buffer
        self.current_waveform = None
        self.current_rms_error = 0.0
        self._err_history = deque(maxlen=10)  # Rolling average for stable ERR
        self.active_ref_name = "SAW"  # Current snapped REF shape name
        self.phase_inverted = False   # Manual phase flip for 180° correction
        self.phase_offset = 0.0      # Manual horizontal shift (0-1 maps to 0-128 samples)
        self.body_gain = 1.0         # Body scalar: 0.25x-1.0x shrinks ideal inside hw peak
        self.v_offset = 0.0          # Vertical DC offset: ±0.2 for asymmetric high/low

        # Generator info (set externally for snapshot provenance)
        self.current_generator_id = ""
        self.current_synthdef_name = ""
        self.app_version = ""

        # Ideal overlay generator
        self.ideal = IdealOverlay(128)

    # -----------------------------------------------------------------
    # Enable / disable
    # -----------------------------------------------------------------

    def enable(self, slot: int, rate: int = None):
        """Enable telemetry for a specific slot."""
        if not 0 <= slot < 8:
            logger.warning(f"[Telemetry] Invalid slot: {slot}")
            return

        if rate is None:
            rate = self.MONITOR_RATE
        rate = max(1, min(60, rate))
        self.target_slot = slot
        self.current_rate = rate
        self.enabled = True
        self.history.clear()
        self.current_waveform = None

        slot_idx = slot + 1

        # EXCLUSIVE BRANCHING:
        # INTERNAL: Start infrastructure tap. Waveform started separately if needed.
        if self._capture_type == self.CAPTURE_INTERNAL:
            self.osc.send('telem_tap_enable', [slot_idx, rate])
        # EXTERNAL: Configure embedded telemetry.
        else:
            self.osc.send('telem_enable', [slot_idx, rate])

        logger.info(f"[Telemetry] Enabled slot {slot} at {rate}Hz (capture: {self._capture_type})")

    def disable(self):
        """Disable telemetry and waveform capture."""
        if self.enabled:
            slot_idx = self.target_slot + 1

            # Always clean up internal tap (harmless if not running)
            if self._capture_type == self.CAPTURE_INTERNAL:
                self.osc.send('telem_tap_enable', [slot_idx, 0])
                if self.waveform_active:
                    self.disable_waveform(self.target_slot)

            # Always clean up external config
            self.osc.send('telem_enable', [slot_idx, 0])

            self.waveform_active = False
            self.enabled = False
            self.current_waveform = None
            logger.info("[Telemetry] Disabled")

    def set_rate(self, rate: int):
        """Change telemetry rate without resetting state."""
        if not self.enabled:
            return
        rate = max(1, min(60, rate))
        if rate == self.current_rate:
            return
        self.current_rate = rate

        slot_idx = self.target_slot + 1

        if self._capture_type == self.CAPTURE_INTERNAL:
            self.osc.send('telem_tap_enable', [slot_idx, rate])
        else:
            self.osc.send('telem_enable', [slot_idx, rate])

        logger.info(f"[Telemetry] Rate changed to {rate}Hz")

    def set_slot(self, slot: int):
        """Switch to monitoring a different slot.

        Tears down internal capture on old slot.
        Optimistically starts internal tap on new slot (to ensure immediate meters).
        set_generator_context() will correct this if the new slot ends up being External.
        """
        if not 0 <= slot < 8:
            return
        old_slot = self.target_slot

        if self.enabled:
            old_idx = old_slot + 1

            # 1. Tear down OLD slot based on KNOWN capture type
            if self._capture_type == self.CAPTURE_INTERNAL:
                self.osc.send('telem_tap_enable', [old_idx, 0])
                if self.waveform_active:
                    self.disable_waveform(old_slot)

            # Disable external telemetry on old slot (harmless if internal)
            self.osc.send('telem_enable', [old_idx, 0])

            # 2. Setup NEW slot
            self.target_slot = slot
            new_idx = slot + 1

            # Optimistically start Internal Tap.
            # If the new generator is External, set_generator_context will stop this shortly.
            # This prevents "dead meters" during the context switch lag.
            self.osc.send('telem_tap_enable', [new_idx, self.current_rate])

            # NOTE: We do NOT auto-start waveform capture here.
            # We let set_generator_context() handle that once it determines the
            # correct capture type (Internal vs External) to avoid unnecessary synth churn.

            self.history.clear()
            self.current_waveform = None
        else:
            self.target_slot = slot

    def set_generator_context(self, name: str, synthdef: str):
        """Update the current generator context and ensure correct capture type.

        This is the AUTHORITY for the internal synth lifecycle.
        """
        self.current_generator_id = name or ""
        self.current_synthdef_name = synthdef or ""

        new_type = self.CAPTURE_EXTERNAL if self.is_hw_mode else self.CAPTURE_INTERNAL
        old_type = self._capture_type
        self._capture_type = new_type

        # Ensure correct synths are running for the new type.
        if self.enabled:
            slot_idx = self.target_slot + 1

            if new_type == self.CAPTURE_INTERNAL:
                # INTERNAL: Ensure infrastructure tap is RUNNING
                self.osc.send('telem_tap_enable', [slot_idx, self.current_rate])

                # If UI wants waveform, ensure internal capture is RUNNING
                if self.waveform_active:
                    self.enable_waveform(self.target_slot)

            else:  # EXTERNAL
                # EXTERNAL: Ensure infrastructure synths are STOPPED
                self.osc.send('telem_tap_enable', [slot_idx, 0])
                self.osc.send('telem_wave_enable', [slot_idx, 0])

                # Ensure embedded telemetry is RUNNING
                self.osc.send('telem_enable', [slot_idx, self.current_rate])

        if old_type != new_type:
            logger.info(f"[Telemetry] Capture type: {old_type} -> {new_type}")

    @property
    def is_hw_mode(self) -> bool:
        """True when monitoring the Generic Hardware Profiler."""
        return self.current_synthdef_name == self.HW_SYNTHDEF

    @property
    def param_labels(self) -> list:
        """Return param labels appropriate for the current generator."""
        return self.HW_PARAM_LABELS if self.is_hw_mode else self.DEFAULT_PARAM_LABELS

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

        # Live RMS error against the Digital Twin ideal (10-frame rolling average)
        # Inject waveform into latest data so get_ideal_waveform can measure body amp
        latest = self.get_latest()
        if latest is not None:
            latest['waveform'] = self.current_waveform
        ideal = self.get_ideal_waveform(latest)
        if ideal is not None and len(ideal) == len(self.current_waveform):
            diff = np.clip(self.current_waveform - ideal, -5.0, 5.0)
            frame_err = float(np.std(diff))
            self._err_history.append(frame_err)
            self.current_rms_error = sum(self._err_history) / len(self._err_history)
        else:
            self.current_rms_error = 0.0

    # -----------------------------------------------------------------
    # Ideal overlay generation from current telemetry
    # -----------------------------------------------------------------

    def get_ideal_waveform(self, data: dict = None) -> np.ndarray:
        """Generate a universal reference waveform based on the REF (P2) selector.

        REF is quantized (snapped) to three discrete shapes:
            < 0.33: SINE   (snaps to 0.0)
            0.33-0.66: SQUARE (snaps to 0.5, P3/SYM controls duty cycle)
            > 0.66: SAW    (snaps to 1.0)

        User adjusts SYM (P3) and SAT (P4) until ideal matches hardware.
        Returns phase-aligned ideal waveform array, or None if no data.
        """
        if data is None:
            data = self.get_latest()
        if data is None:
            return None

        raw_ref = data.get('p2', 1.0)

        # 1. QUANTIZATION (Snapping) — eliminates dead-zone ambiguity
        if raw_ref < 0.33:
            ref_val = 0.0
            self.active_ref_name = "SINE"
        elif raw_ref < 0.66:
            ref_val = 0.5
            self.active_ref_name = "SQUARE"
        else:
            ref_val = 1.0
            self.active_ref_name = "SAW"

        sym = data.get('p3', 0.5)

        # 2. DYNAMIC SCALING: shape-specific SYM sensitivity
        if ref_val == 0.0:
            sym_mult = 0.3   # Sine: gentle — preserve existing match
            tilt_mult = 0.0
        elif ref_val == 0.5:
            sym_mult = 3.5   # Square: wide pulse-width range
            tilt_mult = 0.0
        else:
            sym_mult = 5.0   # Saw: handle Buchla's curved ramp
            tilt_mult = 1.2  # Aggressive DC tilt for slope matching

        sym_offset = (sym - 0.5) * sym_mult

        if ref_val == 0.0:
            # MODE: PURE SINE
            base_wave = np.sin(self.ideal.t) * 1.0 + sym_offset
        elif ref_val == 0.5:
            # MODE: GENERIC SQUARE — SYM (P3) controls Pulse Width (duty cycle)
            # Trigonometric duty cycle mapping: SYM 0→10%, SYM 1→90%
            duty = 0.1 + (sym * 0.8)
            pw_threshold = float(np.sin((0.5 - duty) * np.pi))
            base_wave = np.where(np.sin(self.ideal.t) > pw_threshold, 1.0, -1.0)

            # Slew limiter: models slow op-amp rise/fall time (SAT/P4 controls rate).
            # Linear mapping decoupled from body gain: 0.05 (slow) to 2.0 (fast).
            sat_raw = data.get('p4', 0.0)
            slew_rate = 0.05 + (sat_raw * 1.95)
            slewed = np.empty_like(base_wave)
            slewed[0] = base_wave[0]
            for n in range(1, len(base_wave)):
                diff = base_wave[n] - slewed[n - 1]
                slewed[n] = slewed[n - 1] + np.clip(diff, -slew_rate, slew_rate)

            base_wave = slewed
        else:
            # MODE: PURE SAWTOOTH — SYM tilts the ramp slope
            saw = self.ideal.ideal_saw_sc()
            base_wave = saw + sym_offset * tilt_mult

        # Saturation: Square uses slew limiter (above), Sine/Saw use tanh curve
        if ref_val != 0.5:
            sat_raw = data.get('p4', 0.0)
            sat_drive = 1.0 + (sat_raw ** 2 * 6.0)
            shaped = np.tanh(base_wave * sat_drive)
            comp = np.tanh(sat_drive) if sat_drive > 1.0 else 1.0
            shaped = shaped / comp
        else:
            shaped = base_wave  # Square already slew-limited + RC filtered

        # =================================================================
        # AMPLITUDE STAGING — Forensic Body Matching
        # =================================================================
        # The 'peak' metric includes transient spikes from slew/ringing and
        # does NOT represent the steady-state plateau voltage. We measure
        # the true body amplitude using 10th/90th percentile plateau
        # detection from the captured waveform, ignoring transient spikes.
        # =================================================================

        hw_wave = data.get('waveform')
        if hw_wave is not None:
            hw_arr = np.asarray(hw_wave, dtype=np.float64)
            # Percentile-based plateau detection: 10th/90th ignores transient
            # spikes that inflate peak (e.g. 0.68V peak vs 0.375V plateau)
            hi = float(np.percentile(hw_arr, 90))
            lo = float(np.percentile(hw_arr, 10))
            hw_body_amp = 0.5 * (hi - lo)
            hw_dc_bias = 0.5 * (hi + lo)
        else:
            # Fallback when no waveform data (buffer not ready / monitor-only).
            # For Square, use rms_stage3 as body proxy — RMS of a perfect square
            # equals its amplitude, avoiding overshoot inflation from peak.
            # For Sine/Saw, peak is appropriate.
            p3_peak = data.get('peak3')
            peak_ref = p3_peak if p3_peak is not None else data.get('peak', 0.66)

            if ref_val == 0.5:
                hw_body_amp = data.get('rms_stage3', peak_ref * 0.707)
            else:
                hw_body_amp = peak_ref
            hw_dc_bias = 0.0

        if ref_val == 0.5:
            # SQUARE: scale to measured body amplitude, not transient peak.
            # body_gain is a fine-tune multiplier around 1.0.
            ideal = shaped * hw_body_amp * self.body_gain
            # Match hardware DC bias first, then add manual offset as trim
            ideal = ideal + hw_dc_bias + self.v_offset
        else:
            # SINE / SAW: use peak3 from SC when available, else legacy peak
            p3_peak = data.get('peak3')
            hw_peak = p3_peak if p3_peak is not None else data.get('peak', 0.66)
            ideal = shaped * hw_peak * self.body_gain
            # DC null: remove mean to prevent SYM from biasing ERR
            ideal = ideal - np.mean(ideal)
            # Vertical offset as manual trim
            if self.v_offset != 0.0:
                ideal = ideal + self.v_offset

        # Phase inversion toggle for 180° correction
        if self.phase_inverted:
            ideal = -ideal

        # Manual phase offset — horizontal slide of ideal over actual
        if self.phase_offset != 0.0:
            shift = int(self.phase_offset * len(ideal))
            ideal = np.roll(ideal, shift)

        return ideal.astype(np.float32)

    def get_delta_waveform(self) -> np.ndarray:
        """Compute |actual - ideal| delta trace for Digital Twin comparison.

        Returns absolute difference array, or None if either waveform
        is unavailable or lengths don't match.
        """
        if self.current_waveform is None:
            return None

        ideal = self.get_ideal_waveform()
        if ideal is None:
            return None

        actual = self.current_waveform
        if len(actual) != len(ideal):
            return None

        return np.abs(actual - ideal).astype(np.float32)

    def get_ideal_rms(self, data: dict = None) -> dict:
        """Compute ideal RMS for each stage from current telemetry params.

        In hardware mode, calculates RMS from the Digital Twin waveform.
        In internal mode, uses the B258 stage model.
        """
        if data is None:
            data = self.get_latest()
        if data is None:
            return None

        if self.is_hw_mode:
            # HW mode: compute RMS from the Digital Twin ideal waveform.
            # Return full S1/S2/S3 keys to prevent UI KeyErrors.
            ideal = self.get_ideal_waveform(data)
            if ideal is not None:
                rms_val = float(np.sqrt(np.mean(ideal ** 2)))
                return {'rms_stage1': 0.0, 'rms_stage2': 0.0, 'rms_stage3': rms_val}
            return {'rms_stage1': 0.0, 'rms_stage2': 0.0, 'rms_stage3': 0.0}

        return self.ideal.ideal_b258_rms(
            p0_sine_sq=data.get('p0', 0),
            p1_sine_saw=data.get('p1', 0),
            p2_mix=data.get('p2', 0.5),
            p3_sym_raw=data.get('p3', 0.5),
            p4_sat=data.get('p4', 0),
        )

    def has_phase_lock_warning(self, data: dict = None) -> bool:
        """Check if Schmidt-measured frequency is at a clamp boundary.

        Returns True when freq is stuck at a known limit, indicating
        the Schmidt trigger is not locking to actual pitch:
        - freq < 1 Hz (no signal / trigger never fired)
        - freq near 2000 Hz (lockout max clamp)
        - freq near 10 Hz (period max clamp)
        - freq near 48000 Hz (sample rate — Timer never triggered)
        """
        if data is None:
            data = self.get_latest()
        if data is None:
            return False
        freq = data.get('freq', 0)
        if freq < 1:
            return True
        return (abs(freq - 2000.0) < 10
                or abs(freq - 10.0) < 1
                or abs(freq - 48000.0) < 100)

    # -----------------------------------------------------------------
    # Auto-Twin optimizer
    # -----------------------------------------------------------------

    def optimize_twin(self) -> dict:
        """Run Nelder-Mead minimization to auto-lock the Digital Twin.

        Searches the parameter space to minimize RMS error between the
        current hardware waveform and the ideal overlay. Shape-aware:
          - Square: 5D (phase, SYM, SAT, body_gain, v_offset)
          - Sine/Saw: 3D (phase, SYM, SAT)

        Returns dict with optimized values and final error, or None if
        no waveform data is available.
        """
        if self.current_waveform is None:
            logger.warning("[Telemetry] optimize_twin: no waveform data")
            return None

        data = self.get_latest()
        if data is None:
            logger.warning("[Telemetry] optimize_twin: no telemetry data")
            return None

        target = self.current_waveform.copy()
        is_square = self.active_ref_name == "SQUARE"

        # Inject waveform into data so get_ideal_waveform can measure body amplitude
        data['waveform'] = target

        # Snapshot current values as starting point
        current_phase = self.phase_offset
        current_sym = data.get('p3', 0.5)
        current_sat = data.get('p4', 0.0)
        current_body = self.body_gain
        current_vofs = self.v_offset

        def cost(params):
            """RMS error between ideal waveform with trial params and actual."""
            if is_square:
                phase, sym, sat, body, vofs = params
            else:
                phase, sym, sat = params
                body = 1.0
                vofs = 0.0

            # Clamp to valid ranges
            phase = float(np.clip(phase, -0.5, 0.5))
            sym = float(np.clip(sym, 0.0, 1.0))
            sat = float(np.clip(sat, 0.0, 1.0))
            body = float(np.clip(body, 0.25, 1.0))
            vofs = float(np.clip(vofs, -0.2, 0.2))

            # Build trial data dict with overridden SYM/SAT
            trial_data = data.copy()
            trial_data['p3'] = sym
            trial_data['p4'] = sat

            # Temporarily set controller state for the trial
            orig_phase = self.phase_offset
            orig_body = self.body_gain
            orig_vofs = self.v_offset
            self.phase_offset = phase
            self.body_gain = body
            self.v_offset = vofs

            ideal = self.get_ideal_waveform(trial_data)

            # Restore
            self.phase_offset = orig_phase
            self.body_gain = orig_body
            self.v_offset = orig_vofs

            if ideal is None or len(ideal) != len(target):
                return 10.0  # Penalty for invalid

            diff = np.clip(target - ideal, -5.0, 5.0)
            return float(np.std(diff))

        # Initial guess and bounds
        if is_square:
            x0 = [current_phase, current_sym, current_sat, current_body, current_vofs]
            bounds = [(-0.5, 0.5), (0.0, 1.0), (0.0, 1.0), (0.25, 1.0), (-0.2, 0.2)]
        else:
            x0 = [current_phase, current_sym, current_sat]
            bounds = [(-0.5, 0.5), (0.0, 1.0), (0.0, 1.0)]

        logger.info(f"[Telemetry] optimize_twin: starting Nelder-Mead ({len(x0)}D, {self.active_ref_name})")

        result = minimize(
            cost, x0,
            method='Nelder-Mead',
            options={'maxiter': 500, 'xatol': 1e-4, 'fatol': 1e-5, 'adaptive': True},
        )

        # Apply optimized values
        if is_square:
            opt_phase, opt_sym, opt_sat, opt_body, opt_vofs = result.x
        else:
            opt_phase, opt_sym, opt_sat = result.x
            opt_body = 1.0
            opt_vofs = 0.0

        opt_phase = float(np.clip(opt_phase, -0.5, 0.5))
        opt_sym = float(np.clip(opt_sym, 0.0, 1.0))
        opt_sat = float(np.clip(opt_sat, 0.0, 1.0))
        opt_body = float(np.clip(opt_body, 0.25, 1.0))
        opt_vofs = float(np.clip(opt_vofs, -0.2, 0.2))

        # Commit to controller state
        self.phase_offset = opt_phase
        self.body_gain = opt_body
        self.v_offset = opt_vofs
        self._err_history.clear()

        final_err = result.fun
        logger.info(
            f"[Telemetry] optimize_twin: done — ERR={final_err:.4f} "
            f"phase={opt_phase:.4f} SYM={opt_sym:.3f} SAT={opt_sat:.3f} "
            f"BODY={opt_body:.3f} OFS={opt_vofs:.4f} "
            f"(iters={result.nit}, evals={result.nfev})"
        )

        return {
            'phase': opt_phase,
            'sym': opt_sym,
            'sat': opt_sat,
            'body_gain': opt_body,
            'v_offset': opt_vofs,
            'error': final_err,
            'iterations': result.nit,
            'evaluations': result.nfev,
            'success': result.success,
            'shape': self.active_ref_name,
        }

    # -----------------------------------------------------------------
    # Preset state
    # -----------------------------------------------------------------

    def get_state(self) -> dict:
        """Return telemetry tuning state for preset save."""
        return {
            'phase_inverted': self.phase_inverted,
            'phase_offset': self.phase_offset,
            'body_gain': self.body_gain,
            'v_offset': self.v_offset,
        }

    def set_state(self, state: dict):
        """Restore telemetry tuning state from preset load."""
        self.phase_inverted = state.get('phase_inverted', False)
        self.phase_offset = state.get('phase_offset', 0.0)
        self.body_gain = state.get('body_gain', 1.0)
        self.v_offset = state.get('v_offset', 0.0)
        self._err_history.clear()

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
            Dict with frame, waveform, ideal, provenance, and hw_dna data.
            None if no telemetry data available.
        """
        if not self.history:
            return None

        latest = self.history[-1].copy()
        # Strip injected numpy arrays only; preserve list-based waveform data
        if isinstance(latest.get('waveform'), np.ndarray):
            del latest['waveform']

        # Include ideal waveform for comparison
        ideal_wave = self.get_ideal_waveform(latest)
        ideal_rms = self.get_ideal_rms(latest)

        # Hardware DNA fields (populated when waveform capture is active)
        hw_dna = self._compute_hw_dna(ideal_wave)

        # Delta trace (Digital Twin visualizer)
        delta_wave = self.get_delta_waveform()

        # Phase lock integrity check
        phase_lock_warning = self.has_phase_lock_warning(latest)

        result = {
            'frame': latest,
            'waveform': (
                self.current_waveform.tolist()
                if self.current_waveform is not None else None
            ),
            'ideal_waveform': (
                ideal_wave.tolist() if ideal_wave is not None else None
            ),
            'delta_waveform': (
                delta_wave.tolist() if delta_wave is not None else None
            ),
            'ideal_rms': ideal_rms,
            'history_length': len(self.history),
            'captured_at': datetime.now().isoformat(),
            'phase_lock_warning': phase_lock_warning,
            'provenance': {
                'generator_id': self.current_generator_id,
                'synthdef': self.current_synthdef_name,
                'git_hash': self._get_git_hash(),
                'noise_engine_version': self.app_version,
                'slot': self.target_slot,
                'telemetry_rate': self.current_rate,
            }
        }

        if hw_dna is not None:
            # Include SYM and SAT from params for DNA provenance
            hw_dna['symmetry'] = latest.get('p3', 0.5)
            hw_dna['saturation'] = latest.get('p4', 0.0)
            hw_dna['rms_stage1'] = latest.get('rms_stage1', 0)
            hw_dna['peak'] = latest.get('peak', 0)
            if phase_lock_warning:
                hw_dna['phase_lock_warning'] = True
            result['hw_dna'] = hw_dna

        return result

    def export_history(self, path: str):
        """Export full telemetry history to JSON."""
        # Strip injected numpy arrays only; preserve list-based waveform data
        clean_history = []
        for frame in self.history:
            f = frame.copy()
            if isinstance(f.get('waveform'), np.ndarray):
                del f['waveform']
            clean_history.append(f)
        data = {
            'history': clean_history,
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

    def _compute_hw_dna(self, ideal_wave) -> dict:
        """Compute hardware DNA profiling fields from waveform capture.

        Returns dict with hw_dc_bias, rms_error, harmonic_signature,
        or None if no waveform data is available.
        """
        if self.current_waveform is None:
            return None

        wave = self.current_waveform
        n = len(wave)

        # DC bias: average value of captured waveform
        hw_dc_bias = float(np.mean(wave))

        # RMS error: std deviation between actual and ideal waveforms
        rms_error = 0.0
        if ideal_wave is not None and len(ideal_wave) == n:
            rms_error = float(np.std(wave - ideal_wave))

        # Harmonic signature: 8-bin FFT magnitude map
        fft = np.fft.rfft(wave)
        magnitudes = np.abs(fft)
        # Bin into 8 bands (skip DC bin)
        n_bins = 8
        band_size = max(1, (len(magnitudes) - 1) // n_bins)
        harmonic_signature = []
        for i in range(n_bins):
            start = 1 + i * band_size
            end = min(1 + (i + 1) * band_size, len(magnitudes))
            if start < len(magnitudes):
                harmonic_signature.append(float(np.mean(magnitudes[start:end])))
            else:
                harmonic_signature.append(0.0)

        return {
            'hw_dc_bias': hw_dc_bias,
            'rms_error': rms_error,
            'harmonic_signature': harmonic_signature,
        }

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
