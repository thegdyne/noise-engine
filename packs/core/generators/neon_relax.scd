// core/neon_relax — Lightweight end-stage generator
/*
Neon Relax Generator
Neon bulb relaxation oscillator inspired by Elektor

Signal flow: Neon Oscillator -> Glow simulation -> Filter -> ENV VCA -> Output

Custom params:
  - P1 strike_voltage: 0-1 (ionization threshold)
  - P2 maintain_voltage: 0-1 (sustain threshold)
  - P3 gas_pressure: 0-1 (affects frequency stability)
  - P4 glow_character: 0-1 (soft <-> harsh glow)
  - P5 flicker: 0-1 (instability/randomness)
*/

SynthDef(\neonRelax, { |out, freqBus, customBus0|
    var sig, freq;
    var p = In.kr(customBus0, 5);
    var strikeV, maintainV, pressure, glowChar, flicker;
    var osc, glow, noise, instability;

    freq = In.kr(freqBus);

    strikeV = p[0];
    maintainV = p[1];
    pressure = p[2];
    glowChar = p[3];
    flicker = p[4];

    // === SOUND SOURCE ===
    instability = LFNoise1.kr(pressure.linexp(0, 1, 2, 20)) * flicker * 0.15;

    osc = LFPulse.ar(freq * (1 + instability), 0, strikeV.linlin(0, 1, 0.1, 0.5));
    glow = SinOsc.ar(freq * 0.5) * maintainV * 0.3;

    sig = osc + glow;
    sig = (sig * glowChar.linexp(0, 1, 1, 4)).softclip;

    noise = PinkNoise.ar * flicker * 0.1 * LFNoise2.kr(20).range(0, 1);
    sig = sig + noise;

    sig = ~stereoSpread.(sig, 0.2, 0.35);
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] neonRelax loaded".postln;
