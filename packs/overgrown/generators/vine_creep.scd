// overgrown/vine_creep — Lightweight end-stage generator
SynthDef(\forge_overgrown_vine_creep, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var growth, tendril, coil, sap, spread;
    var base, coiled, tendrils, wet, mod1, mod2, mod3;

    growth = p[0];
    tendril = p[1];
    coil = p[2];
    sap = p[3];
    spread = p[4];

    freq = In.kr(freqBus);

    // Very slow growth modulations
    mod1 = SinOsc.kr(growth.linexp(0, 1, 0.01, 0.2)).range(0.9, 1.1);
    mod2 = SinOsc.kr(growth.linexp(0, 1, 0.015, 0.3), pi/3).range(0.95, 1.05);
    mod3 = LFNoise1.kr(growth.linexp(0, 1, 0.05, 0.5)).range(0.98, 1.02);

    // Base oscillator - organic sine cluster
    base = SinOsc.ar(freq * mod1) * 0.4;
    base = base + (SinOsc.ar(freq * 2.01 * mod2) * 0.2);
    base = base + (SinOsc.ar(freq * 0.5 * mod3) * 0.3);

    // Coiling - phase modulation spiral
    coiled = SinOsc.ar(freq * mod1, SinOsc.ar(freq * coil.linexp(0, 1, 0.5, 4) * mod2) * coil * 2);
    coiled = coiled * 0.3;

    // Tendrils - higher harmonics with slow random movement
    tendrils = SinOsc.ar(freq * 3 * LFNoise1.kr(0.2).range(0.98, 1.02)) * tendril * 0.15;
    tendrils = tendrils + (SinOsc.ar(freq * 5 * LFNoise1.kr(0.15).range(0.97, 1.03)) * tendril * 0.08);
    tendrils = tendrils + (SinOsc.ar(freq * 7 * LFNoise1.kr(0.1).range(0.96, 1.04)) * tendril * 0.04);

    // Sap wetness - filtered noise
    wet = LPF.ar(BrownNoise.ar(0.1), sap.linexp(0, 1, 200, 1000)) * sap * 0.2;
    wet = wet * LFNoise1.kr(0.3).range(0.5, 1);

    // Combine with stereo spread
    sig = base + coiled + tendrils;
    sig = [sig + (wet * 0.7), sig + (wet * 0.3)];

    // Slow stereo movement
    sig = Balance2.ar(sig[0], sig[1], SinOsc.kr(growth.linexp(0, 1, 0.03, 0.15)).range(spread.neg, spread));

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_overgrown_vine_creep loaded".postln;
