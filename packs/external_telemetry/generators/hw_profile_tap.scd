// external_telemetry/hw_profile_tap — Generic Hardware Profiler
/*
Generic Hardware Profiler — Digital Twin Laboratory

Routes external hardware audio (via MOTU M6 inputs) through the telemetry
system for real-time comparison with IdealOverlay. Use this to:
  - Profile any external synth through the audio interface
  - Compare hardware waveforms against mathematical ideal
  - Extract DC bias, harmonic signature, and saturation curves
  - Build a "Digital Twin" calibration dataset

SAFETY: User must attenuate hardware signal with MOTU M6 front-panel
GAIN knobs until Stage 1 Peak stays below 0.95.

Phase tracking uses Schmidt.ar hysteresis (±0.15) with wide DC offset
correction (RunningSum 16384 samples / ~340ms) and a minimum-period lockout
(24 samples / 2kHz max) for stable zero-crossing detection on noisy,
low-frequency hardware signals (10Hz+).

Waveform capture is embedded (phase-wrapped 128-sample LocalBuf) with a
phase-lock gate that prevents noise from filling the table before lock.
Only emits waveform frames in capture mode (telemetryRate > 10Hz).

Custom params:
  - P0 CHN: MOTU M6 input channel (0-5)
  - P1 LVL: Level normalization multiplier (0-4x)
  - P2 REF: Reference shape selector (0=Sine, 0.5=Square, 1=Saw)
  - P3 SYM: Waveform symmetry matching for Ideal overlay
  - P4 OFF: Unused

Stage contract (mirrors internal generators):
  - Stage 1 (Actual):    Raw hardware input (pre-normalization)
  - Stage 2 (Normalized): Gain-adjusted, clipped ±1 (via P1/LVL)
  - Stage 3 (Reference):  Calibrated benchmark transform (LeakDC + 0.66)

Telemetry taps (when telemetryRate > 0):
  - freq: Schmidt-measured hardware frequency (for Hz labels + lock detection)
  - phase: Period-measured ramp (for overlay alignment)
  - rms/peak: Per-stage amplitude tracking
*/

SynthDef(\forge_hw_profile_tap, { |out, freqBus, customBus0, slotIndex=0, telemetryRate=0|
	var sig, freq, p;
	var hw, hw_dc, stage1, stage2, stage3;
	var phase, badValue;

	// Schmidt hysteresis (±0.15 to ignore analog ringing)
	var sch, rawZc, zc;
	var sampBetween;
	var lockoutSamples = 24; // 2kHz max at 48kHz SR

	// DC offset tracking
	var dcBias;

	// Phase-wrapped waveform capture (128-sample single-cycle table)
	var waveBuf, waveIdx, waveOut;

	// Phase lock gate
	var locked;

	p = In.kr(customBus0, 5);

	// --- 1. HARDWARE INPUT ---
	hw = SoundIn.ar(p[0].round(1).clip(0, 5));
	stage1 = hw;

	// --- 2. PHASE TRACKING (Schmidt ±0.15) ---
	// DC correction: 16384-sample RunningSum (~340ms) averages multiple
	// cycles even at 10Hz, preventing bias from tracking the waveform.
	dcBias = RunningSum.ar(hw, 16384) / 16384;
	hw_dc = hw - dcBias;

	// Schmidt.ar: outputs 1 above +0.15, stays 1 until below -0.15
	sch = Schmidt.ar(hw_dc, -0.15, 0.15);

	// Rising edge → single-sample pulse → lockout debounce
	rawZc = Trig1.ar(sch - Delay1.ar(sch) > 0, SampleDur.ir);
	zc = Trig1.ar(rawZc, lockoutSamples / SampleRate.ir);

	// Period measurement
	sampBetween = (Timer.ar(zc) * SampleRate.ir).clip(
		SampleRate.ir / 2000,
		SampleRate.ir / 10
	);
	freq = SampleRate.ir / sampBetween;

	// Phase lock gate: signal present AND freq in sane audio range
	locked = (Amplitude.ar(stage1, 0.01, 0.1) > 0.005) * (freq > 11) * (freq < 1900);

	// Phase ramp for overlay alignment
	phase = Phasor.ar(trig: zc, rate: (1.0 / sampBetween), start: 0, end: 1.0);

	// --- 3. STAGE CONTRACT ---
	stage2 = (hw * Lag.kr(p[1].clip(0, 4), 0.05)).clip(-1, 1);
	stage3 = LeakDC.ar(stage2, 0.9999) * 0.66;
	badValue = CheckBadValues.ar(stage3, post: 0);

	// --- 4. PHASE-WRAPPED CAPTURE (128 samples) ---
	// .floor prevents fractional smearing; locked gate zeros write on unlock
	waveBuf = LocalBuf(128);
	waveIdx = (phase * 127).floor.clip(0, 127);
	BufWr.ar(stage3 * locked, waveBuf, waveIdx, loop: 1);
	waveOut = BufRd.kr(1, waveBuf, Array.series(128, 0, 1));

	// --- 5. TELEMETRY EMISSION ---
	// Path A: Meters/Params (always when telemetry active)
	SendReply.kr(Impulse.kr(telemetryRate) * (telemetryRate > 0), '/noise/telem/gen', [
		slotIndex,
		A2K.kr(freq), A2K.kr(phase),
		p[0], p[1], p[2], p[3], p[4],
		Amplitude.ar(stage1, 0.01, 0.1),
		Amplitude.ar(stage2, 0.01, 0.1),
		Amplitude.ar(stage3, 0.01, 0.1),
		Peak.ar(stage1, Impulse.kr(telemetryRate.max(0.1))).lag(0.1),
		A2K.kr(badValue)
	]);

	// Path B: Waveform frame (capture mode only, locked only)
	SendReply.kr(
		Impulse.kr(telemetryRate.min(15)) * (telemetryRate > 10) * A2K.kr(locked),
		'/noise/telem/hw_wave',
		[slotIndex] ++ waveOut
	);

	// --- MANDATORY TAIL ---
	ReplaceOut.ar(out, NumChannels.ar(stage3, 2));
}).add;

"  [x] forge_hw_profile_tap loaded (Generic Hardware Profiler)".postln;
