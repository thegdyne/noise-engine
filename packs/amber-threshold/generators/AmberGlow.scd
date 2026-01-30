// amber-threshold/AmberGlow — Lightweight end-stage generator
/*
AMBERGLOW Generator
Warm golden light resonance, soft harmonic shimmer

Features:
  - Rich warm harmonics
  - Gentle shimmering movement
  - Light diffusion texture
  - Dust particles in beams

Custom params:
  - P1 warmth: Golden tone intensity
  - P2 shimmer: Light movement
  - P3 spread: Diffusion width
  - P4 dust: Particle texture
  - P5 ancient: Aged patina
*/

SynthDef(\amberglow, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var warmth, shimmer, spread, dust, ancient;
    var warmSig, shimmerSig, dustSig;
    var warmOsc, shimmerMod;

    freq = In.kr(freqBus);

    warmth = p[0];
    warmth = Lag.kr(warmth, 0.1);
    shimmer = p[1];
    shimmer = Lag.kr(shimmer, 0.1);
    spread = p[2];
    spread = Lag.kr(spread, 0.1);
    dust = p[3];
    dust = Lag.kr(dust, 0.05);
    ancient = p[4];
    ancient = Lag.kr(ancient, 0.2);

    // === WARMTH (golden harmonics) ===
    warmOsc = SinOsc.ar(freq);
    warmOsc = warmOsc + (SinOsc.ar(freq * 2) * 0.5);  // Octave
    warmOsc = warmOsc + (SinOsc.ar(freq * 3) * 0.25);  // 5th
    warmOsc = warmOsc + (SinOsc.ar(freq * 4) * 0.15);  // 2nd octave
    // Warm filtering - emphasize low-mids
    warmOsc = LPF.ar(warmOsc, 1500 + (warmth * 1000));
    warmOsc = warmOsc + (BPF.ar(warmOsc, 400, 0.3) * warmth * 0.5);
    warmSig = warmOsc * warmth * 0.4;

    // === SHIMMER (light dancing) ===
    shimmerMod = LFNoise2.kr(3 + (shimmer * 8)).range(0.95, 1.05);
    shimmerSig = SinOsc.ar(freq * 2 * shimmerMod);
    shimmerSig = shimmerSig + (SinOsc.ar(freq * 3.01 * shimmerMod) * 0.5);
    shimmerSig = shimmerSig * LFNoise1.kr(5 + (shimmer * 10)).range(0.3, 1);
    shimmerSig = HPF.ar(shimmerSig, 800);
    shimmerSig = shimmerSig * shimmer * 0.3;

    // === DUST (particles in light) ===
    dustSig = Dust.ar(dust * 80) * 0.5;
    dustSig = BPF.ar(dustSig, 3000 + (LFNoise1.kr(2).range(0, 2000)), 0.3);
    dustSig = dustSig + (Dust.ar(dust * 40) * BPF.ar(PinkNoise.ar, 1500, 0.2) * 0.3);
    dustSig = dustSig * dust;

    // === SPREAD (diffusion) ===
    sig = warmSig + shimmerSig + dustSig;
    sig = sig + (CombL.ar(sig, 0.1, 0.03 + (spread * 0.02), spread * 0.5) * spread * 0.3);
    sig = sig + (CombL.ar(sig, 0.1, 0.05, spread * 0.4) * spread * 0.2);

    // === ANCIENT (aged quality) ===
    sig = sig + (BPF.ar(PinkNoise.ar, 200, 0.2) * ancient * 0.1);
    sig = LPF.ar(sig, 6000 - (ancient * 2000));

    sig = sig.tanh;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] amberglow loaded".postln;
