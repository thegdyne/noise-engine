// buchla_258/b258_twin — Lightweight end-stage generator
/*
B258 Twin - Buchla 258 Digital Twin

Improved version of b258_osc using fitted parameters from hardware telemetry.
Same control structure, more accurate behavior.

Key improvements from telemetry analysis:
- Control curve: k^1.96 applied to morph controls (wait then surge)
- Fixed h2 asymmetry: 0.54 baked into sine shaper
- Tuned spectral tilt coefficients from measured harmonics

Custom params (same as b258_osc):
- P1 SAW: Sine to Saw morph (with k^1.96 curve)
- P2 SQR: Sine to Square morph (with k^1.96 curve)
- P3 MIX: Balance between Saw branch and Square branch
- P4 SYM: Spectral tilt (saw) or pulse width (square), 0.1-0.9
- P5 SAT: Tanh drive (sine/saw) or slew rate (square), 0.05-0.95

Output: per-branch 1.32 makeup * 0.68 global scalar.
No filter/envelope — handled by channel strip end-stage.
*/

SynthDef(\b258_twin, { |out, freqBus, customBus0|
	var sig, freq, sine, square, saw, branchSaw, branchSqr;
	var p, sawMorph, sqrMorph, mix, sym, sat;
	var sawMorphCurved, sqrMorphCurved;
	var duty, pw_thresh, slew_rate;
	var saw_tilt;

	// Fitted control curve exponent from hardware telemetry
	var curveExp = 1.96;

	// Fitted h2 asymmetry from hardware (~0.54)
	var h2Asymmetry = 0.54;

	p = In.kr(customBus0, 5);
	sawMorph = Lag.kr(p[0], 0.05);  // P1 SAW: Sine -> Saw
	sqrMorph = Lag.kr(p[1], 0.05);  // P2 SQR: Sine -> Square
	mix      = Lag.kr(p[2], 0.05);  // P3 MIX: Saw <-> Square
	sym      = Lag.kr(p[3], 0.05);  // P4 SYM: Tilt / Width
	sat      = Lag.kr(p[4], 0.05);  // P5 SAT: Drive / Slew

	// Apply k^1.96 control curve to morph controls
	// This gives the authentic "wait then surge" behavior
	sawMorphCurved = sawMorph.pow(curveExp);
	sqrMorphCurved = sqrMorph.pow(curveExp);

	freq = In.kr(freqBus).clip(5, 20000);

	// --- 1. SINE BRANCH (with h2 asymmetry from telemetry) ---
	// The 0.54 h2 asymmetry creates slight even-harmonic content
	// Implemented via asymmetric soft-clip (positive peaks slightly harder)
	sine = SinOsc.ar(freq);
	// Asymmetric saturation: positive side gets slightly more drive
	sine = ((sine * (1 + (sine.max(0) * h2Asymmetry * 0.1))) * (1 + (sat * 0.01))).tanh * 1.32;

	// --- 2. SQUARE BRANCH (Forensic DNA: Gold Lock) ---
	// A. Pulse Width: Decoupled 10-90% mapping from SYM
	duty = 0.1 + (sym * 0.8);
	// Threshold for sine comparison: sin((0.5 - duty) * pi)
	pw_thresh = sin((0.5 - duty) * pi);
	// Generate square from sine threshold
	square = (SinOsc.ar(freq) > pw_thresh).madd(2, -1);

	// B. Linear Slew Rate (units/sec, pitch-invariant)
	slew_rate = (0.05 + (sat * 1.95)) * SampleRate.ir;
	square = Slew.ar(square, slew_rate, slew_rate);

	// Morph: Sine -> Square (with k^1.96 curve)
	branchSqr = XFade2.ar(sine, square, sqrMorphCurved.linlin(0, 1, -1, 1));

	// --- 3. SAW BRANCH (Forensic DNA: Spectral Tilt Filter) ---
	// A. Band-limited base
	saw = LFSaw.ar(freq);

	// B. Spectral Tilt (OnePole LowPass) - tuned from telemetry
	// SYM 0.0 (Dark) -> 0.5 (Natural) -> 1.0 (Bright)
	saw_tilt = sym.linlin(0, 1, 0.9, 0.0);
	saw = OnePole.ar(saw, saw_tilt);

	// C. Saturation with h2 asymmetry
	saw = ((saw * (1 + (saw.max(0) * h2Asymmetry * 0.1))) * (1 + (sat * 0.01))).tanh * 1.32;

	// Morph: Sine -> Saw (with k^1.96 curve)
	branchSaw = XFade2.ar(sine, saw, sawMorphCurved.linlin(0, 1, -1, 1));

	// --- 4. MIX & OUTPUT ---
	// MIX 0 = Saw branch, MIX 1 = Square branch
	sig = XFade2.ar(branchSaw, branchSqr, mix.linlin(0, 1, -1, 1));

	// Output scalar: targets ~0.68 peak at telemetry tap
	sig = sig * 0.68;

	// --- MANDATORY TAIL ---
	sig = NumChannels.ar(sig, 2);
	ReplaceOut.ar(out, sig);
}).add;

"  [x] b258_twin loaded".postln;
