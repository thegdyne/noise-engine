// buchla_258/b258_twin — Lightweight end-stage generator
/*
B258 Twin - Buchla 258 Digital Twin

ADDITIVE SYNTHESIS using ALL fitted parameters from 12-point hardware telemetry.
This generator recreates the EXACT harmonic behavior measured from real hardware.

=== FITTED MODEL (r² > 0.89) ===

Control law:     s(k) = k^1.96  (convex "wait then surge")
Harmonic decay:  E(n) = exp(-0.177 * n)
Gaussian bump:   G(n) = exp(-0.5 * ((n - 3.54) / 0.64)²)
Sensitivity:     F(n) = 0.17 + 0.14 * G(n)

Harmonic formula: h_n(k) = baseline_n + k * E(n) * F(n)

Baseline values at morph=0:
  h1 = 1.0 (fundamental, normalized)
  h2 = 0.523 (fixed asymmetry - the 258's "soul")
  h3 = 0.049
  h4 = 0.018
  h5 = 0.015
  h6 = 0.006
  h7 = 0.003
  h8 = 0.001

=== CONTROL MAPPING ===

P1 SAW: Morph for saw-like spectrum (all harmonics, 1/n rolloff bias)
P2 SQR: Morph for square-like spectrum (odd harmonics emphasized)
P3 MIX: Blend between SAW and SQR character
P4 SYM: h2 asymmetry amount (0=none, 0.5=measured, 1=double)
P5 SAT: Bump intensity (controls h3/h4 prominence)

Output: RMS-normalized with headroom.
No filter/envelope — handled by channel strip end-stage.
*/

SynthDef(\b258_twin, { |out, freqBus, customBus0|
	var sig, freq;
	var params, sawMorph, sqrMorph, mix, sym, sat;
	var sawK, sqrK, k;
	var brightnessScale, h2Scale;
	var h1, h2, h3, h4, h5, h6, h7, h8;
	var h3saw, h4saw, h5saw, h6saw, h7saw, h8saw;
	var h3sqr, h4sqr, h5sqr, h6sqr, h7sqr, h8sqr;
	var theta, rmsGain;

	// =======================================================
	// FITTED MODEL CONSTANTS (from hardware telemetry)
	// =======================================================
	var curveExp = 1.96;    // Control curve exponent
	var capB = 0.177;       // Harmonic decay rate
	var mu = 3.54;          // Gaussian bump center (h3/h4)
	var sigma = 0.64;       // Gaussian bump width
	var c0 = 0.17;          // Base sensitivity
	var c1 = 0.14;          // Bump sensitivity

	// Baseline harmonics at morph=0 (measured from hardware)
	var h2Base = 0.523;     // The 258's characteristic asymmetry
	var h3Base = 0.049;
	var h4Base = 0.018;
	var h5Base = 0.015;
	var h6Base = 0.006;
	var h7Base = 0.003;
	var h8Base = 0.001;

	// Gaussian bump values (pre-calculated for each harmonic)
	var g3 = exp(-0.5 * ((3 - mu) / sigma).squared);  // ~0.68
	var g4 = exp(-0.5 * ((4 - mu) / sigma).squared);  // ~0.73
	var g5 = exp(-0.5 * ((5 - mu) / sigma).squared);  // ~0.21
	var g6 = exp(-0.5 * ((6 - mu) / sigma).squared);  // ~0.01
	var g7 = exp(-0.5 * ((7 - mu) / sigma).squared);  // ~0.00
	var g8 = exp(-0.5 * ((8 - mu) / sigma).squared);  // ~0.00

	// Exponential decay values (pre-calculated)
	var e3 = exp(-1 * capB * 3);  // ~0.59
	var e4 = exp(-1 * capB * 4);  // ~0.49
	var e5 = exp(-1 * capB * 5);  // ~0.41
	var e6 = exp(-1 * capB * 6);  // ~0.35
	var e7 = exp(-1 * capB * 7);  // ~0.29
	var e8 = exp(-1 * capB * 8);  // ~0.24

	// =======================================================
	// INPUTS
	// =======================================================
	params = In.kr(customBus0, 5);
	sawMorph = Lag.kr(params[0], 0.05);  // P1 SAW
	sqrMorph = Lag.kr(params[1], 0.05);  // P2 SQR
	mix      = Lag.kr(params[2], 0.05);  // P3 MIX
	sym      = Lag.kr(params[3], 0.05);  // P4 SYM (h2 amount)
	sat      = Lag.kr(params[4], 0.05);  // P5 SAT (bump intensity)

	freq = In.kr(freqBus).clip(5, 20000);

	// =======================================================
	// CONTROL CURVES (k^1.96 - the "wait then surge")
	// =======================================================
	sawK = sawMorph.pow(curveExp);
	sqrK = sqrMorph.pow(curveExp);

	// Combined morph amount (mixed between saw and sqr paths)
	k = (sawK * (1 - mix)) + (sqrK * mix);

	// =======================================================
	// USER-CONTROLLED SCALING
	// =======================================================
	// SYM controls h2 asymmetry (0=none, 0.51=measured, 1=2x measured)
	h2Scale = sym.linlin(0.1, 0.9, 0.0, 2.0);

	// SAT controls bump intensity (how much h3/h4 "pop")
	brightnessScale = sat.linlin(0.05, 0.95, 0.3, 2.0);

	// =======================================================
	// HARMONIC COEFFICIENTS (using full fitted model)
	// h_n(k) = baseline + k * E(n) * F(n)
	// where F(n) = c0 + c1 * G(n) * brightnessScale
	// =======================================================
	h1 = 1.0;
	h2 = h2Base * h2Scale;

	// SAW path: all harmonics (1/n natural rolloff from saw spectrum)
	h3saw = h3Base + (sawK * e3 * (c0 + (c1 * g3 * brightnessScale)));
	h4saw = h4Base + (sawK * e4 * (c0 + (c1 * g4 * brightnessScale)));
	h5saw = h5Base + (sawK * e5 * (c0 + (c1 * g5 * brightnessScale)));
	h6saw = h6Base + (sawK * e6 * (c0 + (c1 * g6 * brightnessScale)));
	h7saw = h7Base + (sawK * e7 * (c0 + (c1 * g7 * brightnessScale)));
	h8saw = h8Base + (sawK * e8 * (c0 + (c1 * g8 * brightnessScale)));

	// SQR path: odd harmonics emphasized (even harmonics reduced)
	h3sqr = h3Base + (sqrK * e3 * (c0 + (c1 * g3 * brightnessScale)) * 1.2);  // odd: boost
	h4sqr = h4Base + (sqrK * e4 * (c0 + (c1 * g4 * brightnessScale)) * 0.3);  // even: reduce
	h5sqr = h5Base + (sqrK * e5 * (c0 + (c1 * g5 * brightnessScale)) * 1.2);  // odd: boost
	h6sqr = h6Base + (sqrK * e6 * (c0 + (c1 * g6 * brightnessScale)) * 0.3);  // even: reduce
	h7sqr = h7Base + (sqrK * e7 * (c0 + (c1 * g7 * brightnessScale)) * 1.2);  // odd: boost
	h8sqr = h8Base + (sqrK * e8 * (c0 + (c1 * g8 * brightnessScale)) * 0.3);  // even: reduce

	// MIX blends between SAW and SQR harmonic structures
	h3 = (h3saw * (1 - mix)) + (h3sqr * mix);
	h4 = (h4saw * (1 - mix)) + (h4sqr * mix);
	h5 = (h5saw * (1 - mix)) + (h5sqr * mix);
	h6 = (h6saw * (1 - mix)) + (h6sqr * mix);
	h7 = (h7saw * (1 - mix)) + (h7sqr * mix);
	h8 = (h8saw * (1 - mix)) + (h8sqr * mix);

	// =======================================================
	// ADDITIVE SYNTHESIS
	// Phase-aligned partials for clean harmonic spectrum
	// =======================================================
	theta = Phasor.ar(0, freq / SampleRate.ir, 0, 2pi);

	sig = (h1 * SinOsc.ar(0, theta))
	    + (h2 * SinOsc.ar(0, theta * 2))
	    + (h3 * SinOsc.ar(0, theta * 3))
	    + (h4 * SinOsc.ar(0, theta * 4))
	    + (h5 * SinOsc.ar(0, theta * 5))
	    + (h6 * SinOsc.ar(0, theta * 6))
	    + (h7 * SinOsc.ar(0, theta * 7))
	    + (h8 * SinOsc.ar(0, theta * 8));

	// =======================================================
	// NORMALIZATION
	// RMS-based gain compensation for consistent output level
	// =======================================================
	rmsGain = (h1.squared + h2.squared + h3.squared + h4.squared +
	           h5.squared + h6.squared + h7.squared + h8.squared).sqrt.max(0.001).reciprocal;
	sig = sig * rmsGain * 0.7;

	// --- MANDATORY TAIL ---
	sig = NumChannels.ar(sig, 2);
	ReplaceOut.ar(out, sig);
}).add;

"  [x] b258_twin loaded (additive synthesis from hardware telemetry)".postln;
