// sgwd/mist — Lightweight end-stage generator
// mist: Fine spray from waterfall impact
SynthDef(\forge_sgwd_mist, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var spray, fine, drift, cool, veil;

    spray = p[0].linlin(0, 1, 0.5, 1);
    fine = p[1].linexp(0, 1, 800, 3000);
    drift = p[2].linlin(0, 1, 0.1, 0.8);
    cool = p[3].linlin(0, 1, 0.3, 0.7);
    veil = p[4].linlin(0, 1, 0.4, 0.8);

    freq = In.kr(freqBus);

    // DSP: Mist - continuous noise bed is key
    // Strong continuous base
    sig = PinkNoise.ar(0.5) + BrownNoise.ar(0.3);
    sig = LPF.ar(sig, 2000);

    // Spray texture
    sig = sig + BPF.ar(WhiteNoise.ar(spray * 0.4), fine, 0.5);

    // Cool air breath
    sig = sig + (LPF.ar(PinkNoise.ar(cool * 0.4), 1500));

    // Gentle drift modulation
    sig = sig * LFNoise1.kr(drift * 0.5).range(0.8, 1);

    sig = sig * 0.5;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_sgwd_mist loaded".postln;
