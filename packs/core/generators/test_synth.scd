// core/test_synth — Lightweight end-stage generator
/*
Test Synth Generator
Simple sine oscillator for testing signal flow

Signal flow: Sine -> Filter -> ENV VCA -> Output
*/

SynthDef(\testSynth, { |out, freqBus, customBus0|
    var sig, freq;

    freq = In.kr(freqBus);

    // === SOUND SOURCE ===
    sig = SinOsc.ar(freq) * 0.5;


    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] testSynth loaded".postln;
