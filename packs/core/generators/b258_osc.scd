// core/b258_osc — Lightweight end-stage generator
/*
Buchla 258 Dual Oscillator — Forensic DNA Implementation

Based on profiled hardware DNA from Generic Hardware Profiler captures:
  - Sine Branch: Rounded peaks via tanh soft-clip, SAT controls drive (1x-2.5x)
  - Square Branch: SinOsc threshold for pulse width + linear Slew rate (Gold Lock)
  - Saw Branch: LFSaw + OnePole spectral tilt (matches buchla_saw.json harmonics)

Custom params:
  - P1 SAW: Sine to Saw morph (XFade2 crossfade)
  - P2 SQR: Sine to Square morph (XFade2 crossfade)
  - P3 MIX: Balance between Saw branch and Square branch
  - P4 SYM: Spectral tilt (saw) or pulse width (square), 0.1-0.9
  - P5 SAT: Tanh drive (sine/saw) or slew rate (square), 0.05-0.95

Output: Raw signal; 0.38 plateau handled by output_trim_db (-8.4 dB).
No filter/envelope — handled by channel strip end-stage.
*/

SynthDef(\forge_core_b258_osc, { |out, freqBus, customBus0|
	var sig, freq, sine, square, saw, branchSaw, branchSqr;
	var p, sawMorph, sqrMorph, mix, sym, sat;
	var duty, pw_thresh, slew_rate;
	var saw_tilt;

	p = In.kr(customBus0, 5);
	sawMorph = Lag.kr(p[0], 0.05);  // P1 SAW: Sine -> Saw
	sqrMorph = Lag.kr(p[1], 0.05);  // P2 SQR: Sine -> Square
	mix      = Lag.kr(p[2], 0.05);  // P3 MIX: Saw <-> Square
	sym      = Lag.kr(p[3], 0.05);  // P4 SYM: Tilt / Width
	sat      = Lag.kr(p[4], 0.05);  // P5 SAT: Drive / Slew

	freq = In.kr(freqBus).clip(5, 20000);

	// --- 1. SINE BRANCH (DNA: rounded peaks via tanh soft-clip) ---
	// Drive range: 1.0 (clean) to 2.5 (saturated) matches buchla_sine1.json
	sine = (SinOsc.ar(freq) * (1 + (sat * 1.5))).tanh;

	// --- 2. SQUARE BRANCH (Forensic DNA: Gold Lock) ---
	// A. Pulse Width: Decoupled 10-90% mapping from SYM
	duty = 0.1 + (sym * 0.8);
	// Threshold for sine comparison: sin((0.5 - duty) * pi)
	pw_thresh = sin((0.5 - duty) * pi);
	// Generate square from sine threshold
	square = (SinOsc.ar(freq) > pw_thresh).madd(2, -1);

	// B. Linear Slew Rate (units/sec, pitch-invariant)
	// 0.05 (slow) to 2.0 (instant). Matches close2.json calibration.
	slew_rate = (0.05 + (sat * 1.95)) * SampleRate.ir;
	square = Slew.ar(square, slew_rate, slew_rate);

	// Morph: Sine -> Square
	branchSqr = XFade2.ar(sine, square, sqrMorph.linlin(0, 1, -1, 1));

	// --- 3. SAW BRANCH (Forensic DNA: Spectral Tilt Filter) ---
	// A. Band-limited base (straight ramp, no bending)
	saw = LFSaw.ar(freq);

	// B. Spectral Tilt (OnePole LowPass) matches buchla_saw.json harmonics
	// SYM 0.0 (Dark) -> 0.5 (Natural) -> 1.0 (Bright)
	// Coef: 0.9 (Heavy LP) -> 0.0 (Open)
	saw_tilt = sym.linlin(0, 1, 0.9, 0.0);
	saw = OnePole.ar(saw, saw_tilt);

	// C. Saturation (match sine/square peak behavior)
	saw = (saw * (1 + (sat * 1.5))).tanh;

	// Morph: Sine -> Saw
	branchSaw = XFade2.ar(sine, saw, sawMorph.linlin(0, 1, -1, 1));

	// --- 4. MIX & OUTPUT ---
	// MIX 0 = Saw branch, MIX 1 = Square branch
	sig = XFade2.ar(branchSaw, branchSqr, mix.linlin(0, 1, -1, 1));

	// --- MANDATORY TAIL ---
	sig = NumChannels.ar(sig, 2);
	ReplaceOut.ar(out, sig);
}).add;

"  [x] forge_core_b258_osc loaded".postln;
