// rlyeh/madness — Lightweight end-stage generator
// madness: Sanity shattering - the mind breaks
SynthDef(\forge_rlyeh_madness, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var fracture, spiral, voices, paranoia, hysteria;

    fracture = p[0].linlin(0, 1, 0, 0.3);  // P1: Reality fracture
    spiral = p[1].linlin(0, 1, 0.5, 8);  // P2: Descending spiral rate
    voices = p[2].linlin(0, 1, 0, 0.6);  // P3: Whispering voices
    paranoia = p[3].linlin(0, 1, 1, 20);  // P4: Paranoid jitter
    hysteria = p[4].linlin(0, 1, 0, 0.7);  // P5: Hysterical FM

    freq = In.kr(freqBus);

    // DSP: Fractured oscillators
    sig = SinOsc.ar(freq * (1 + (LFNoise2.kr(paranoia) * fracture)));
    sig = sig + (Saw.ar(freq * 0.5 * (1 + (LFNoise2.kr(paranoia * 0.7) * fracture * 0.5))) * 0.5);

    // Descending spiral
    sig = sig * SinOsc.kr(spiral).range(0.3, 1);

    // Whispering voices (granular noise)
    sig = sig + (BPF.ar(PinkNoise.ar(voices), freq * LFNoise0.kr(8).range(1, 4), 0.1) * 2);

    // Hysterical FM
    sig = sig + (SinOscFB.ar(freq * 2, hysteria * 0.8) * hysteria * 0.3);

    sig = sig * 0.25;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_rlyeh_madness loaded".postln;
