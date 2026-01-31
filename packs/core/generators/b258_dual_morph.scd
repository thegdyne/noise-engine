// core/b258_dual_morph — Lightweight end-stage generator with telemetry
/*
B258 Dual Morph Generator — True 258 Logic
Single sine seed physically deformed through nonlinear shaping.

Features:
  - Waveshaping architecture: SinOsc seed, no independent oscillators
  - Branch A: Sine to Square via high-gain saturation + hard clip
  - Branch B: Sine to Saw via phase-synced ramp integration
  - Symmetry injected pre-clip for authentic PWM and tilt
  - XFade2 crossfade between shaping topologies
  - Optional telemetry taps (zero overhead when disabled)

Custom params:
  - P1 sine_sqr: Sine to Square morph (gain into clip)
  - P2 sine_saw: Sine to Saw morph (phase distortion blend)
  - P3 mix: Balance between Square and Saw branches
  - P4 symmetry: DC bias for PWM (square) and slope tilt (saw)
  - P5 saturation: Final analog warmth via tanh drive

Telemetry taps (when telemetryRate > 0):
  - stage1: Pure sine seed (line 48)
  - stage2: Post-morph XFade2 output (line 63)
  - stage3: Final output post-LeakDC (line 69)
*/

SynthDef(\forge_core_b258_dual_morph, { |out, freqBus, customBus0, slotIndex=0, telemetryRate=0|
    var sig, freq, p;
    var p0_sineSq, p1_sineSaw, p2_mix, p3_sym, p4_sat;
    var sine, sqr, saw;
    var stage1, stage2, stage3;  // Telemetry taps
    var phase, badValue;

    // Contiguous 5-channel custom bus read
    p = In.kr(customBus0, 5);

    // --- PARAMETER MAPPING (Elastic Smoothing) ---
    p0_sineSq  = Lag.kr(p[0], 0.05);
    p1_sineSaw = Lag.kr(p[1], 0.05);
    p2_mix     = Lag.kr(p[2], 0.05);
    p3_sym     = Lag.kr(p[3].linlin(0, 1, -0.85, 0.85), 0.06);
    p4_sat     = Lag.kr(p[4], 0.08);

    // Frequency: Clamped to 5Hz - 20kHz range
    freq = In.kr(freqBus).clip(5, 20000);

    // Phase tracking for Python sync (normalized 0-1)
    phase = Phasor.ar(0, freq * SampleDur.ir, 0, 1);

    // --- SINE SEED ---
    sine = SinOsc.ar(freq, 0);
    stage1 = sine;  // TAP: Pure sine input

    // --- BRANCH A: SINE TO SQUARE (High Gain Clipping) ---
    // Symmetry/bias applied before clipping = PWM effect
    sqr = (sine + p3_sym) * p0_sineSq.linexp(0, 1, 1, 120);
    sqr = sqr.clip2(1.0);

    // --- BRANCH B: SINE TO SAW (Phase Distortion) ---
    // Warp sine into saw by mixing in phase-synced ramp
    saw = (sine * (1 - p1_sineSaw)) + (LFSaw.ar(freq, 1) * p1_sineSaw);
    saw = (saw + (p3_sym * 0.5)).clip2(1.0);

    // --- MIX: Balance between Square and Saw branches ---
    sig = XFade2.ar(sqr, saw, p2_mix.linlin(0, 1, -1, 1));
    stage2 = sig;  // TAP: Post-morph output

    // --- FINAL SATURATION ---
    sig = (sig * p4_sat.linexp(0, 1, 1, 18)).tanh;

    // Output stage — relaxed DC block + calibrated gain
    sig = LeakDC.ar(sig, 0.9998) * 0.85;
    stage3 = sig;  // TAP: Final output

    // Bad value detection (catches NaN/inf from extreme settings)
    badValue = CheckBadValues.ar(sig, post: 0);

    // === TELEMETRY (only active when telemetryRate > 0) ===
    // Impulse.kr(0) fires once at init; gate it with (telemetryRate > 0) for true silence
    SendReply.kr(Impulse.kr(telemetryRate) * (telemetryRate > 0), '/noise/telem/gen', [
        slotIndex,                              // Slot index for routing
        freq,                                   // Current frequency
        A2K.kr(phase),                          // Normalized 0-1 phase
        p[0], p[1], p[2], p[3], p[4],          // P0-P4 raw values
        Amplitude.ar(stage1, 0.01, 0.1),        // RMS of pure sine
        Amplitude.ar(stage2, 0.01, 0.1),        // RMS after morph
        Amplitude.ar(stage3, 0.01, 0.1),        // RMS final output
        Peak.ar(sig, Impulse.kr(telemetryRate.max(0.1))).lag(0.1),  // Peak level
        A2K.kr(badValue)                        // 0=clean, 1=NaN, 2=inf
    ]);

    // --- MANDATORY TAIL ---
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] forge_core_b258_dual_morph loaded (with telemetry)".postln;
