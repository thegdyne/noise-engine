// drowned_temple/rubble — Lightweight end-stage generator
// rubble: Collapsed stone and debris
SynthDef(\forge_drowned_temple_rubble, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var crumble, impact, scatter, grind, settle;

    crumble = p[0].linlin(0, 1, 2, 20);  // P1: Crumble rate
    impact = p[1].linlin(0, 1, 0.2, 0.8);  // P2: Impact weight
    scatter = p[2].linlin(0, 1, 5, 40);  // P3: Scatter density
    grind = p[3].linlin(0, 1, 0, 0.5);  // P4: Grinding friction
    settle = p[4].linlin(0, 1, 0.1, 0.5);  // P5: Settling dust

    freq = In.kr(freqBus);

    // DSP: Stone impacts - low thuds
    sig = Ringz.ar(Dust.ar(crumble) * impact, freq * [0.5, 0.7, 1], 0.15) * 0.4;

    // Scatter - small debris
    sig = sig + (Ringz.ar(Dust.ar(scatter) * 0.15, freq * [2, 3, 4.5], 0.03) * 0.5);

    // Grinding friction
    sig = sig + (LPF.ar(Crackle.ar(1.7) * grind * 0.3, freq * 3));

    // Settling dust - continuous filtered noise
    sig = sig + (LPF.ar(PinkNoise.ar(settle), 600) * 0.4);

    sig = sig * 0.4;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_drowned_temple_rubble loaded".postln;
