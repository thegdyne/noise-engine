// _example/sine_drone — Lightweight end-stage generator
/*
Sine Drone Generator (Example Pack)
Simple sine-based drone with harmonics and vibrato

Custom params:
  - P1 harmonics: 0-1 (pure sine to rich harmonics)
  - P2 detune: 0-1 (stereo detune spread)
  - P3 vibrato: 0-1 (vibrato depth)
*/

SynthDef(\example_sine_drone, { |out, freqBus, customBus0|
    var sig, freq;
    var p = In.kr(customBus0, 3);
    var harmonics, detune, vibrato;
    var vibLfo, freqL, freqR, sig1, sig2, sig3;

    freq = In.kr(freqBus);

    harmonics = p[0];
    detune = p[1];
    vibrato = p[2];

    // === SOUND SOURCE ===
    vibLfo = SinOsc.kr(5) * vibrato * 0.02;
    freqL = freq * (1 + vibLfo) * (1 - (detune * 0.01));
    freqR = freq * (1 + vibLfo) * (1 + (detune * 0.01));

    // Fundamental + harmonics blend
    sig1 = SinOsc.ar([freqL, freqR]);
    sig2 = SinOsc.ar([freqL, freqR] * 2) * 0.5;
    sig3 = SinOsc.ar([freqL, freqR] * 3) * 0.25;

    sig = sig1 + ((sig2 + sig3) * harmonics);
    sig = sig * 0.5;  // Normalize

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] example_sine_drone loaded".postln;
