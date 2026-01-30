// pripyat/echo — Lightweight end-stage generator
SynthDef(\forge_pripyat_echo, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var size, conc, empt, drip, chill;
    var exciter, combs, dripSig, delayTime, decayTime, dripRate;

    freq = In.kr(freqBus);

    size = p[0];
    conc = p[1];
    empt = p[2];
    drip = p[3];
    chill = p[4];

    // Continuous noise bed for drone mode
    exciter = PinkNoise.ar(0.05);
    // Add sparse impulses
    exciter = exciter + (Dust.ar(empt.linexp(0, 1, 3, 0.5)) * 0.3);

    // Water drips
    dripRate = drip.linexp(0, 1, 0.5, 4);
    dripSig = Dust.ar(dripRate);
    dripSig = Ringz.ar(dripSig, freq * LFNoise0.kr(dripRate).range(2, 6), 0.15) * drip * 0.5;

    // Add drips to exciter
    exciter = exciter + dripSig;

    // Delay time based on size (room dimensions)
    delayTime = size.linexp(0, 1, 0.01, 0.15);
    decayTime = size.linlin(0, 1, 0.5, 4) * (1 - (chill * 0.5));

    // Multiple comb filters for concrete resonance
    combs = CombL.ar(exciter, 0.2, delayTime, decayTime);
    combs = combs + CombL.ar(exciter, 0.2, delayTime * 0.7, decayTime * 0.8);
    combs = combs + CombL.ar(exciter, 0.2, delayTime * 1.3, decayTime * 0.9);

    // Pitch the resonance
    sig = Resonz.ar(combs, freq, conc.linexp(0, 1, 0.5, 0.1));
    sig = sig * conc.linlin(0, 1, 2, 8); // Gain compensation for resonance

    // Cold dampening - reduce highs
    sig = LPF.ar(sig, chill.linexp(0, 1, 12000, 2000));

    // Add some of the raw combs for body
    sig = sig + (combs * 0.5);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_pripyat_echo loaded".postln;
