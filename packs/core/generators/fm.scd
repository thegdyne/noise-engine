// core/fm — Lightweight end-stage generator
/*
FM Generator
Frequency modulation synthesis with multiple algorithms

Signal flow: Operators -> Algorithm -> Filter -> ENV VCA -> Output

Custom params:
  - P1 ratio: 0.5-8.0 (modulator:carrier ratio)
  - P2 index: 0-20 (modulation depth)
  - P3 index_env: 0-1 (index envelope amount - decay)
  - P4 algorithm: 0-7 discrete (operator routing)
  - P5 feedback: 0-1 (operator self-feedback)
*/

SynthDef(\fm, { |out, freqBus, customBus0|
    var sig, freq;
    var p = In.kr(customBus0, 5);
    var ratio, index, indexEnv, algorithm, feedback;
    var modFreq, car, mod1, mod2, fb, indexMod;

    freq = In.kr(freqBus);

    ratio = p[0];
    index = p[1];
    indexEnv = p[2];
    algorithm = p[3];
    feedback = p[4];

    // === SOUND SOURCE ===
    modFreq = freq * ratio;
    indexMod = index * (1 - (indexEnv * 0.8));

    fb = LocalIn.ar(1) * feedback * 2pi;
    mod1 = SinOsc.ar(modFreq + fb, mul: indexMod * modFreq);
    LocalOut.ar(mod1 / (indexMod * modFreq + 0.001));

    mod2 = SinOsc.ar(modFreq * 2, mul: indexMod * 0.5 * modFreq);

    // Simple algorithm selection
    sig = SelectX.ar(algorithm.min(3), [
        SinOsc.ar(freq + mod1),
        SinOsc.ar(freq + mod1 + mod2),
        SinOsc.ar(freq + (mod1 * mod2 / (modFreq + 1))),
        SinOsc.ar(freq) + (SinOsc.ar(freq * 2 + mod1) * 0.5)
    ]) * 0.5;


    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] fm loaded".postln;
