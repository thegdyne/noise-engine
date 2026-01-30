// bed_stuy/corner — Lightweight end-stage generator
// corner: Street corner ambience
SynthDef(\forge_bed_stuy_corner, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var traffic, voices, sirens, subway, night;

    traffic = p[0].linlin(0, 1, 0.2, 0.7);  // P1: Traffic drone
    voices = p[1].linlin(0, 1, 0, 0.4);  // P2: Distant voices
    sirens = p[2].linlin(0, 1, 0, 0.3);  // P3: Siren wail
    subway = p[3].linlin(0, 1, 0.1, 0.5);  // P4: Subway rumble
    night = p[4].linlin(0, 1, 500, 3000);  // P5: Night filter

    freq = In.kr(freqBus);

    // DSP: Traffic - continuous filtered noise
    sig = LPF.ar(BrownNoise.ar(traffic), 300) * 0.6;

    // Distant voices - filtered bursts
    sig = sig + (BPF.ar(PinkNoise.ar(voices), freq * 4 * LFNoise0.kr(0.5).range(0.8, 1.2), 0.2) * LFNoise1.kr(0.3).range(0.3, 1));

    // Siren wail - distant
    sig = sig + (SinOsc.ar(800 * LFTri.kr(0.3).range(0.9, 1.5)) * sirens * LFNoise1.kr(0.1).range(0, 1) * 0.1);

    // Subway rumble
    sig = sig + (LPF.ar(PinkNoise.ar(subway), 80) * LFNoise1.kr(0.05).range(0.3, 1));

    // Night filter
    sig = LPF.ar(sig, night);

    sig = sig * 0.5;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_bed_stuy_corner loaded".postln;
