// external_telemetry/hw_assessment_tap — Hardware DNA Probe
/*
Hardware Assessment Tap — Phase 1: Digital Twin Profiling

Routes external hardware audio (via MOTU M6 inputs) through the telemetry
system for real-time comparison with IdealOverlay. Use this to:
  - Profile a physical synth (Buchla 258, etc.) through the audio interface
  - Compare hardware waveforms against mathematical ideal
  - Extract DC bias, harmonic signature, and saturation curves
  - Build a "Digital Twin" calibration dataset

SAFETY: User must attenuate hardware signal with MOTU M6 front-panel
GAIN knobs until Stage 1 Peak stays below 0.95.

Phase tracking uses Schmidt.ar hysteresis (±0.15) with wide DC offset
correction (RunningSum 16384 samples / ~340ms) and a minimum-period lockout
(24 samples / 2kHz max) for stable zero-crossing detection on noisy,
low-frequency hardware signals (10Hz+).
Telemetry reports measured freq for Hz labels, Schmitt phase for overlay.
Waveform capture is embedded (phase-wrapped 128-sample LocalBuf) — bypasses
the external forge_telemetry_wave_capture synth for DC-bias-immune capture.

Custom params:
  - P0 CHN: MOTU M6 input channel (0-5)
  - P1 LVL: Level normalization multiplier (0-4x)
  - P2 MIX: Reserved for Phase 2 (Hardware/Digital blend)
  - P3 SYM: Sent to telemetry for IdealOverlay DC bias alignment
  - P4 SAT: Sent to telemetry for IdealOverlay saturation matching

Stage contract (mirrors internal generators):
  - Stage 1 (Actual):    Raw hardware input (pre-normalization)
  - Stage 2 (Normalized): Gain-adjusted, clipped ±1 (via P1/LVL)
  - Stage 3 (Reference):  Calibrated benchmark transform (LeakDC + 0.66)

Telemetry taps (when telemetryRate > 0):
  - freq: Schmidt-measured hardware frequency (for Hz labels + lock detection)
  - phase: Period-measured ramp (for overlay alignment)
  - rms/peak: Per-stage amplitude tracking
*/

SynthDef(\forge_core_hw_assessment_tap, { |out, freqBus, customBus0, slotIndex=0, telemetryRate=0|
	var sig, freq, p;
	var hw, hw_dc, stage1, stage2, stage3;
	var phase, badValue;

	// Schmidt hysteresis variables
	var schmittLo = -0.15, schmittHi = 0.15;
	var sch, rawZc, zc;
	var sampBetween;
	// Minimum-period lockout: 24 samples = 2kHz max at 48kHz SR
	var lockoutSamples = 24;

	// DC offset tracking
	var dcBias;

	// Phase-wrapped waveform capture (128-sample single-cycle table)
	var waveBuf, waveIdx, waveOut;

	// Contiguous 5-channel custom bus read
	p = In.kr(customBus0, 5);

	// --- HARDWARE INPUT (DC-coupled bypass) ---
	// Select MOTU M6 input by channel param
	hw = SoundIn.ar(p[0].round(1).clip(0, 5));

	// Stage 1: Raw hardware input (before any processing)
	stage1 = hw;

	// --- DC OFFSET CORRECTION (for Schmitt trigger only) ---
	// RunningSum over 16384 samples (~340ms at 48kHz) averages multiple
	// cycles even at 10Hz, preventing the bias from tracking the waveform.
	// This does NOT affect stage1/stage2/stage3 — only phase tracking.
	dcBias = RunningSum.ar(hw, 16384) / 16384;
	hw_dc = hw - dcBias;

	// --- SCHMIDT-TRIGGERED PHASE SYNC ---
	// Schmidt.ar: outputs 1 when signal rises above schmittHi,
	// stays 1 until signal falls below schmittLo, then outputs 0.
	// Rising edge (0→1 transition) = one clean zero-crossing per cycle.
	sch = Schmidt.ar(hw_dc, schmittLo, schmittHi);

	// Rising edge detection: single-sample pulse on 0→1 transition
	rawZc = Trig1.ar(sch - Delay1.ar(sch) > 0, SampleDur.ir);

	// Minimum-period lockout — reject re-triggers from analog ringing.
	// Trig1 holds HIGH for lockoutSamples after each accepted trigger,
	// blocking subsequent rawZc pulses until the holdoff expires.
	zc = Trig1.ar(rawZc, lockoutSamples / SampleRate.ir);

	// Period measurement (sample-accurate frequency tracking)
	sampBetween = (Timer.ar(zc) * SampleRate.ir).clip(
		SampleRate.ir / 2000,  // Max 2kHz (matches lockout)
		SampleRate.ir / 10     // Min 10Hz
	);
	freq = SampleRate.ir / sampBetween;

	// High-fidelity phase ramp for Python overlay alignment
	phase = Phasor.ar(trig: zc, rate: (1.0 / sampBetween), start: 0, end: 1.0);

	// --- NORMALIZED STAGE ---
	// Stage 2: Gain-adjusted, clipped to safe range
	stage2 = (hw * Lag.kr(p[1].clip(0, 4), 0.05)).clip(-1, 1);

	// --- OUTPUT STAGE ---
	// Same chain as B258/Reference Sine for apples-to-apples comparison
	sig = LeakDC.ar(stage2, 0.9999) * 0.66;
	stage3 = sig;

	// Bad value detection
	badValue = CheckBadValues.ar(sig, post: 0);

	// --- PHASE-WRAPPED WAVEFORM CAPTURE ---
	// 128-sample LocalBuf written by phase index — creates a stable
	// single-cycle picture regardless of frequency. Immune to DC bias
	// because it uses the Schmidt-derived phase ramp.
	waveBuf = LocalBuf(128);
	waveIdx = (phase * 127).clip(0, 127);
	BufWr.ar(stage3, waveBuf, waveIdx, loop: 1);
	// Read back the full table at control rate for the OSC payload
	waveOut = BufRd.kr(1, waveBuf, Array.series(128, 0, 1));

	// === TELEMETRY (only active when telemetryRate > 0) ===
	// Path A: Standard metrics (freq, phase, params, RMS, peak)
	SendReply.kr(Impulse.kr(telemetryRate) * (telemetryRate > 0), '/noise/telem/gen', [
		slotIndex,
		A2K.kr(freq),                                    // Schmidt-measured hardware frequency
		A2K.kr(phase),                                   // Period-measured phase ramp (overlay alignment)
		p[0], p[1], p[2], p[3], p[4],                   // P0-P4 raw values
		Amplitude.ar(stage1, 0.01, 0.1),                 // RMS of raw hardware
		Amplitude.ar(stage2, 0.01, 0.1),                 // RMS of normalized
		Amplitude.ar(stage3, 0.01, 0.1),                 // RMS of output
		Peak.ar(stage1, Impulse.kr(telemetryRate.max(0.1))).lag(0.1),  // Peak of RAW input
		A2K.kr(badValue)
	]);

	// Path B: Waveform frame (128 phase-wrapped samples)
	// Sent via internal SendReply → relayed to Python by telemetry_tap.scd
	SendReply.kr(
		Impulse.kr(telemetryRate.min(15)) * (telemetryRate > 0),
		'/noise/telem/hw_wave',
		[slotIndex] ++ waveOut
	);

	// --- MANDATORY TAIL ---
	sig = NumChannels.ar(sig, 2);
	ReplaceOut.ar(out, sig);
}).add;

"  [x] forge_core_hw_assessment_tap loaded (Hardware DNA Probe)".postln;
