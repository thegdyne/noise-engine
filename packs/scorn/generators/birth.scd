// scorn/birth — Lightweight end-stage generator
// birth: Pod emergence - opening, wet release
SynthDef(\forge_scorn_birth, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var emerge, sac, fluid, strain, newborn;

    emerge = p[0].linlin(0, 1, 0.3, 1);  // P1: Emergence level
    sac = p[1].linlin(0, 1, 0.2, 0.8);  // P2: Sac membrane
    fluid = p[2].linlin(0, 1, 5, 25);  // P3: Fluid sounds
    strain = p[3].linlin(0, 1, 0.1, 0.5);  // P4: Straining
    newborn = p[4].linlin(0, 1, 0.1, 0.6);  // P5: New life sounds

    freq = In.kr(freqBus);

    // DSP: Sac membrane - stretching sounds
    sig = LPF.ar(PinkNoise.ar(sac * 0.4), 800 * LFNoise1.kr(0.2).range(0.5, 2));

    // Fluid release - wet drips and splashes
    sig = sig + (Ringz.ar(Dust.ar(fluid) * 0.2, freq * [1, 2, 3], 0.08) * emerge * 0.4);

    // Straining sounds - low groans
    sig = sig + (LPF.ar(Saw.ar(freq * 0.25 * LFNoise1.kr(0.3).range(0.9, 1.1)) * strain, 400) * 0.3);

    // Newborn presence - high soft tones
    sig = sig + (SinOsc.ar(freq * [2, 3] * LFNoise1.kr(0.1).range(0.98, 1.02)) * newborn * 0.2);

    // Continuous wet ambience
    sig = sig + (LPF.ar(BrownNoise.ar(emerge * 0.3), 500));

    sig = sig * 0.5;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_scorn_birth loaded".postln;
