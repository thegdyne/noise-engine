// core/ms20 — Lightweight end-stage generator
/*
MS-20 Generator
Korg MS-20 inspired semi-modular synth

Features:
  - Two oscillators (saw + pulse)
  - Ring modulator
  - Aggressive Korg-style filter with drive
  - High-pass filter (MS-20 has both HP and LP)
  - Pink/white noise mixer

Custom params:
  - P1 osc_mix: OSC1 (saw) / OSC2 (pulse) balance
  - P2 ring: Ring modulation amount
  - P3 filter_drive: Pre-filter saturation (Korg character)
  - P4 hpf: High-pass filter frequency
  - P5 noise: Noise level
*/

SynthDef(\ms20, { |out, freqBus, customBus0|
    var sig, freq;
    var p = In.kr(customBus0, 5);
    var oscMix, ring, filterDrive, hpfAmt, noiseLevel;
    var osc1, osc2, ringMod, noise;
    var hpfFreq, filtered;

    freq = In.kr(freqBus);

    oscMix = p[0];
    ring = p[1];
    filterDrive = p[2];
    hpfAmt = p[3];
    noiseLevel = p[4];

    // === OSCILLATORS ===
    // OSC1: Sawtooth
    osc1 = Saw.ar(freq);

    // OSC2: Pulse with slight detune
    osc2 = Pulse.ar(freq * 1.002, 0.5);

    // Mix oscillators
    sig = (osc1 * (1 - oscMix)) + (osc2 * oscMix);

    // === RING MODULATOR ===
    ringMod = osc1 * osc2;
    sig = XFade2.ar(sig, ringMod, ring.linlin(0, 1, -1, 1));

    // === NOISE ===
    noise = PinkNoise.ar;
    sig = sig + (noise * noiseLevel * 0.5);

    // === MS-20 FILTER CHARACTER ===
    // Pre-filter drive (this is key to the MS-20 sound)
    sig = (sig * (1 + (filterDrive * 4))).tanh;

    // High-pass filter (MS-20 has HP before LP)
    hpfFreq = hpfAmt.linexp(0, 1, 20, 2000);
    sig = HPF.ar(sig, hpfFreq);

    // Low-pass filter with aggressive resonance
    // MS-20 filter self-oscillates and screams at high res
    // Using MoogFF for that aggressive character
    filtered = MoogFF.ar(sig, filterFreq, rq.linlin(0.1, 1.0, 3.5, 0) * 0.95);

    // Blend based on filter type (LP/HP/BP modes)
    sig = Select.ar(filterType, [
        filtered,  // LP
        HPF.ar(sig, filterFreq),  // HP
        BPF.ar(sig, filterFreq, rq, 2)  // BP
    ]);

    // === OUTPUT ===
    sig = ~stereoSpread.(sig, 0.1, 0.2);
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] ms20 loaded".postln;
