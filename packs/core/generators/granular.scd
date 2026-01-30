// core/granular — Lightweight end-stage generator
/*
Granular Generator
Micro-sample cloud synthesis using sine grains

Signal flow: Grain Triggers -> Grain Synthesis -> Filter -> ENV VCA -> Output

Custom params:
  - P1 pitch_shift: -24 to +24 semitones
  - P2 grain_size: 0.01-0.5s (grain duration)
  - P3 grain_density: 1-100 grains/sec
  - P4 position_jitter: 0-1 (pitch/time randomness)
  - P5 stereo_spread: 0-1 (pan width)
*/

SynthDef(\granular, { |out, freqBus, customBus0|
    var sig, freq;
    var p = In.kr(customBus0, 5);
    var pitchShift, grainSize, density, jitter, spread;
    var grainTrig, grainFreq, grainDur, pan;

    freq = In.kr(freqBus);

    pitchShift = p[0];
    grainSize = p[1];
    density = p[2];
    jitter = p[3];
    spread = p[4];

    // === SOUND SOURCE ===
    grainTrig = Impulse.ar(density);
    grainFreq = freq * (2 ** (pitchShift / 12));
    grainFreq = grainFreq * (1 + (TRand.ar(-1, 1, grainTrig) * jitter * 0.2));
    grainFreq = grainFreq.clip(20, 20000);

    grainDur = grainSize * (1 + (TRand.ar(-0.5, 0.5, grainTrig) * jitter));
    grainDur = grainDur.clip(0.005, 0.5);

    pan = TRand.ar(-1, 1, grainTrig) * spread;

    sig = GrainSin.ar(
        numChannels: 2,
        trigger: grainTrig,
        dur: grainDur,
        freq: grainFreq,
        pan: pan,
        mul: 0.3
    );

    sig = sig + GrainSin.ar(
        numChannels: 2,
        trigger: Dust.ar(density * 0.3),
        dur: grainDur * 0.5,
        freq: grainFreq * TRand.ar(0.99, 1.01, grainTrig),
        pan: TRand.ar(-1, 1, Dust.ar(density * 0.3)) * spread,
        mul: 0.1
    );

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] granular loaded".postln;
