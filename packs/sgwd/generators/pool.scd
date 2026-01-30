// sgwd/pool — Lightweight end-stage generator
// pool: Dark reflective pool beneath falls
SynthDef(\forge_sgwd_pool, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var depth, dark, ripple, still, reflect;

    depth = p[0].linlin(0, 1, 0.5, 2);  // P1: Pool depth (decay)
    dark = p[1].linexp(0, 1, 200, 80);  // P2: Dark water tone (LPF)
    ripple = p[2].linlin(0, 1, 0.5, 4);  // P3: Surface ripples
    still = p[3].linlin(0, 1, 0.3, 0.9);  // P4: Stillness factor
    reflect = p[4].linlin(0, 1, 0.1, 0.4);  // P5: Shimmer

    freq = In.kr(freqBus);

    // DSP: Deep dark pool
    // Deep sub drone
    sig = SinOsc.ar(freq * 0.5 * LFNoise1.kr(0.1).range(0.99, 1.01)) * 0.4;
    sig = sig + (LFTri.ar(freq * 0.25) * 0.2);

    // Dark filtered noise bed
    sig = sig + (LPF.ar(BrownNoise.ar(0.3), dark) * still);

    // Gentle ripples
    sig = sig + (Ringz.ar(Dust.ar(ripple) * 0.15, freq * [1, 2, 3], depth * 0.3).sum);

    // Reflective shimmer
    sig = sig + (SinOsc.ar(freq * [4, 5, 6] * LFNoise1.kr(0.2).range(0.98, 1.02)) * reflect * 0.1).sum;

    sig = sig * 0.4;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_sgwd_pool loaded".postln;
