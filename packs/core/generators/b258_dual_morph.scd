// core/b258_dual_morph — Lightweight end-stage generator
/*
B258 Dual Morph Generator — True 258 Logic
Single sine seed physically deformed through nonlinear shaping.

Features:
  - Waveshaping architecture: SinOsc seed, no independent oscillators
  - Branch A: Sine to Square via high-gain saturation + hard clip
  - Branch B: Sine to Saw via phase-synced ramp integration
  - Symmetry injected pre-clip for authentic PWM and tilt
  - XFade2 crossfade between shaping topologies

Custom params:
  - P1 sine_sqr: Sine to Square morph (gain into clip)
  - P2 sine_saw: Sine to Saw morph (phase distortion blend)
  - P3 mix: Balance between Square and Saw branches
  - P4 symmetry: DC bias for PWM (square) and slope tilt (saw)
  - P5 saturation: Final analog warmth via tanh drive
*/

SynthDef(\forge_core_b258_dual_morph, { |out, freqBus, customBus0|
    var sig, freq, p;
    var p0_sineSq, p1_sineSaw, p2_mix, p3_sym, p4_sat;
    var sine, sqr, saw;

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

    // --- SINE SEED ---
    sine = SinOsc.ar(freq, 0);

    // --- BRANCH A: SINE TO SQUARE (High Gain Clipping) ---
    // Symmetry/bias applied before clipping = PWM effect
    sqr = (sine + p3_sym) * p0_sineSq.linexp(0, 1, 1, 120);
    sqr = sqr.clip2(0.85);
    sqr = LeakDC.ar(sqr);

    // --- BRANCH B: SINE TO SAW (Phase Distortion) ---
    // Warp sine into saw by mixing in phase-synced ramp
    saw = (sine * (1 - p1_sineSaw)) + (LFSaw.ar(freq, 1, p1_sineSaw));
    saw = (saw + (p3_sym * 0.5)).clip2(0.9);
    saw = LeakDC.ar(saw);

    // --- MIX: Balance between Square and Saw branches ---
    sig = XFade2.ar(sqr, saw, p2_mix.linlin(0, 1, -1, 1));

    // --- FINAL SATURATION ---
    sig = (sig * p4_sat.linexp(0, 1, 1, 18)).tanh;

    // Output stage
    sig = LeakDC.ar(sig) * 0.8;

    // --- MANDATORY TAIL ---
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] forge_core_b258_dual_morph loaded".postln;
