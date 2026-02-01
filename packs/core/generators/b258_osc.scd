// core/b258_osc — Lightweight end-stage generator
/*
Buchla 258 Dual Oscillator — Hardware DNA Implementation

Based on profiled hardware DNA from Generic Hardware Profiler captures:
  - Sine Branch: Rounded peaks via soft-clip tanh, SAT controls drive
  - Square Branch: Linear slew rate models vintage op-amp rise/fall
  - Saw Branch: Asymmetric ramp tilt via symmetry warping

Custom params:
  - P1 SHP: Sine to Square morph (XFade2 crossfade)
  - P2 MOR: Sine to Saw morph (XFade2 crossfade)
  - P3 MIX: Balance between Square branch and Saw branch
  - P4 SYM: Pulse width (square) or ramp tilt (saw), 0.1-0.9
  - P5 SAT: Slew rate (square) or tanh drive (sine/saw), 0.05-0.95

Output: Raw signal; 0.38 plateau handled by output_trim_db (-8.4 dB).
No filter/envelope — handled by channel strip end-stage.
*/

SynthDef(\forge_core_b258_osc, { |out, freqBus, customBus0|
	var sig, freq, phase, sine, square, saw, branchA, branchB;
	var p, shpA, shpB, mix, sym, sat;

	p = In.kr(customBus0, 5);
	shpA = Lag.kr(p[0], 0.05);
	shpB = Lag.kr(p[1], 0.05);
	mix  = Lag.kr(p[2], 0.05);
	sym  = Lag.kr(p[3], 0.06);
	sat  = Lag.kr(p[4], 0.08);

	freq = In.kr(freqBus).clip(5, 20000);

	// Core phase accumulator (0-1 ramp, resets each cycle)
	phase = Phasor.ar(0, freq * SampleDur.ir, 0, 1);

	// 1. SINE BRANCH (DNA: rounded peaks via tanh soft-clip)
	sine = (SinOsc.ar(freq) * (1 + (sat * 0.5))).tanh;

	// 2. SQUARE BRANCH (DNA: linear slew models op-amp rise/fall)
	// sym maps to pulse width: phase > threshold gives +1/-1 square
	square = ((phase > sym) * 2) - 1;
	// Slew.ar rate is units/second; scale by freq for pitch-invariant rise/fall.
	// sat 0.05 → slow ramp, sat 0.95 → near-instant transition.
	square = Slew.ar(square, sat * freq * 8, sat * freq * 8);

	// 3. SAW BRANCH (DNA: Buchla asymmetric ramp tilt)
	// sym warps the ramp shape: 0.5 = linear saw, < 0.5 = concave, > 0.5 = convex
	saw = (phase.pow(1.0 + ((sym - 0.5) * 2)) * 2) - 1;

	// MORPHING LOGIC — XFade2 crossfade between branches
	branchA = XFade2.ar(sine, square, (shpA * 2) - 1);
	branchB = XFade2.ar(sine, saw,    (shpB * 2) - 1);
	sig = XFade2.ar(branchA, branchB, (mix * 2) - 1);

	// DNA calibration: 0.38 plateau now handled by output_trim_db (-8.4 dB)
	// Raw signal preserved for telemetry tap analysis

	// --- MANDATORY TAIL ---
	sig = NumChannels.ar(sig, 2);
	ReplaceOut.ar(out, sig);
}).add;

"  [x] forge_core_b258_osc loaded".postln;
