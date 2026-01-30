// rlyeh/cthulhu — Lightweight end-stage generator
// cthulhu: The Great Old One - massive eldritch presence rising
SynthDef(\forge_rlyeh_cthulhu, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var mass, geometry, dread, voice, dream;
    var subSig, geoSig, dreadSig, voiceSig, dreamSig;

    mass = p[0].linlin(0, 1, 0.2, 1);  // P1: Sub-bass mass
    geometry = p[1].linlin(0, 1, 0, 0.5);  // P2: Non-Euclidean harmonics
    dread = p[2].linlin(0, 1, 0.1, 2);  // P3: Dread throb rate
    voice = p[3].linlin(0, 1, 0, 0.6);  // P4: Eldritch voice
    dream = p[4].linlin(0, 1, 0, 0.4);  // P5: Dream shimmer

    freq = In.kr(freqBus);

    // DSP: Massive sub presence
    subSig = SinOsc.ar(freq / 2) + (SinOsc.ar(freq / 4) * 0.5);
    subSig = subSig * mass * LFNoise1.kr(0.1).range(0.7, 1);

    // Non-Euclidean geometry - impossible intervals
    geoSig = SinOsc.ar(freq * [1, 1.059, 1.189, 1.414]) * geometry;
    geoSig = Splay.ar(geoSig, 0.5) * 0.3;

    // Dread throb
    dreadSig = SinOsc.ar(freq) * SinOsc.kr(dread).range(0, 1) * 0.3;

    // Eldritch voice - formant drone
    voiceSig = Formant.ar(freq * 0.5, freq * 2 * LFNoise1.kr(0.2).range(0.8, 1.2), freq * 4) * voice * 0.2;

    // Dream transmission shimmer
    dreamSig = SinOsc.ar(freq * [3, 4.01, 5.02]) * LFNoise1.kr(0.3).range(0.3, 1) * dream * 0.15;
    dreamSig = Splay.ar(dreamSig, 0.7);

    sig = subSig + geoSig + dreadSig + voiceSig + dreamSig;
    sig = sig * 0.25;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_rlyeh_cthulhu loaded".postln;
