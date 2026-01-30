// sgwd/canopy — Lightweight end-stage generator
// canopy: Lush green overhead
SynthDef(\forge_sgwd_canopy, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var leaves, rustle, filt, drip, breeze;

    leaves = p[0].linlin(0, 1, 0.4, 0.8);
    rustle = p[1].linlin(0, 1, 0.5, 3);
    filt = p[2].linexp(0, 1, 1200, 500);
    drip = p[3].linlin(0, 1, 2, 12);
    breeze = p[4].linlin(0, 1, 0.3, 0.7);

    freq = In.kr(freqBus);

    // DSP: Canopy - continuous noise base
    // Strong continuous filtered noise
    sig = LPF.ar(PinkNoise.ar(0.5), filt);
    sig = sig + BrownNoise.ar(0.25);

    // Leaf rustle texture
    sig = sig + BPF.ar(PinkNoise.ar(leaves * 0.4), 1500 * LFNoise1.kr(rustle).range(0.7, 1.3), 0.4);

    // Breeze modulation
    sig = sig * LFNoise1.kr(0.3).range(0.7, 1);
    sig = sig + (BPF.ar(WhiteNoise.ar(breeze * 0.3), 1200, 0.4));

    // Continuous drip bed
    sig = sig + (Ringz.ar(Dust.ar(drip) * 0.25, freq * [3, 4, 5], 0.12).sum);

    sig = sig * 0.45;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_sgwd_canopy loaded".postln;
