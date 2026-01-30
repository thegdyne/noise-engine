// mirrors/echo — Lightweight end-stage generator
SynthDef(\forge_mirrors_echo, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var surface, reflect, bounce, sizeParam, hollow;
    var exciter, modes, ringTime, hollowRes;

    surface = p[0];
    reflect = p[1];
    bounce = p[2];
    sizeParam = p[3];
    hollow = p[4];

    freq = In.kr(freqBus);

    // Exciter - continuous + bouncing impacts
    exciter = PinkNoise.ar(0.15) + (Dust.ar(bounce.linexp(0, 1, 1, 10)) * 0.5);

    // Ring time based on concrete surface
    ringTime = surface.linexp(0, 1, 0.15, 0.6);

    // Concrete modal resonances
    modes = Ringz.ar(exciter, freq * (0.8 + (sizeParam * 0.4)), ringTime, 0.3 * reflect);
    modes = modes + Ringz.ar(exciter, freq * 1.6 * (0.9 + (sizeParam * 0.2)), ringTime * 0.7, 0.25 * reflect);
    modes = modes + Ringz.ar(exciter, freq * 2.3, ringTime * 0.5, 0.2 * reflect * surface);
    modes = modes + Ringz.ar(exciter, freq * 3.1, ringTime * 0.4, 0.15 * reflect * surface);
    modes = modes + Ringz.ar(exciter, freq * 4.5, ringTime * 0.3, 0.1 * reflect);

    // Low structural mode
    modes = modes + Ringz.ar(exciter, freq * 0.5, ringTime * 1.4, 0.25);

    sig = modes * 0.5;

    // Hollow interior resonance
    hollowRes = CombL.ar(sig, 0.2, freq.reciprocal.clip(0.01, 0.2), 0.3 + (hollow * 0.5), hollow * 0.4);
    sig = sig + hollowRes;

    // Concrete texture
    sig = sig + BPF.ar(BrownNoise.ar(0.15), freq * 0.7, 0.3) * 2;

    // Continuous bed
    sig = sig + LPF.ar(PinkNoise.ar(0.1), 350);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_mirrors_echo loaded".postln;
