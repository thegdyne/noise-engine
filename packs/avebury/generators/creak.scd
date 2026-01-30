// avebury/creak — Lightweight end-stage generator
SynthDef(\forge_avebury_creak, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var stress, aged, branch, wind, groan;
    var exciter, modes, windTrig, stressTrig, ringTime, creakNoise;

    stress = p[0];
    aged = p[1];
    branch = p[2];
    wind = p[3];
    groan = p[4];

    freq = In.kr(freqBus);

    // Wind triggered excitation
    windTrig = Dust.ar(wind.linexp(0, 1, 0.5, 8));

    // Stress creak - filtered noise bursts
    stressTrig = windTrig * LFNoise2.kr(2).range(0, 1);
    creakNoise = BPF.ar(
        Crackle.ar(1.8 + (stress * 0.15), 0.5),
        freq * LFNoise1.kr(3).range(0.8, 2.5),
        0.15
    );
    creakNoise = creakNoise * Decay.ar(stressTrig, 0.2 + (aged * 0.4));

    // Ring time based on age
    ringTime = aged.linexp(0, 1, 0.2, 1.2);

    // Exciter - continuous friction + impacts
    exciter = PinkNoise.ar(0.15) + (windTrig * 0.4);

    // Modal resonances - wood beam modes
    // Branch thickness affects modal spacing
    modes = Ringz.ar(exciter, freq, ringTime, 0.25);
    modes = modes + Ringz.ar(exciter, freq * (1.5 + (branch * 0.5)), ringTime * 0.7, 0.2);
    modes = modes + Ringz.ar(exciter, freq * (2.2 + (branch * 0.8)), ringTime * 0.5, 0.15);
    modes = modes + Ringz.ar(exciter, freq * (3.1 + branch), ringTime * 0.35, 0.1);

    // Deep groan - low frequency modes
    modes = modes + Ringz.ar(exciter, freq * 0.5, ringTime * 1.5, 0.3 * groan);
    modes = modes + Ringz.ar(exciter, freq * 0.25, ringTime * 2, 0.25 * groan);

    sig = modes * 0.4;

    // Add creak texture
    sig = sig + (creakNoise * stress);

    // Wood friction noise
    sig = sig + BPF.ar(BrownNoise.ar(0.1), freq * 0.7, 0.3) * 2;

    // Continuous low bed
    sig = sig + LPF.ar(BrownNoise.ar(0.1), 200);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_avebury_creak loaded".postln;
