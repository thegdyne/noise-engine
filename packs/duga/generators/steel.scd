// duga/steel — Lightweight end-stage generator
SynthDef(\forge_duga_steel, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var gust, tube, wire, ratt, cold;
    var windNoise, gustMod, tubeSig, wireSig, rattSig, combs;

    freq = In.kr(freqBus);

    gust = p[0];
    tube = p[1];
    wire = p[2];
    ratt = p[3];
    cold = p[4];

    // Wind gust modulation - always some wind
    gustMod = LFNoise2.kr(gust.linexp(0, 1, 0.1, 1)).range(0.5, 1);
    gustMod = gustMod * LFNoise2.kr(0.2).range(0.7, 1);

    // Base wind noise - continuous
    windNoise = PinkNoise.ar(1) * (0.3 + (gustMod * 0.4));

    // Comb resonators for hollow tubes
    combs = CombL.ar(windNoise, 0.1, freq.reciprocal, tube.linlin(0, 1, 0.1, 1));
    combs = combs + CombL.ar(windNoise, 0.1, (freq * 1.5).reciprocal, tube.linlin(0, 1, 0.1, 0.8));
    combs = combs + CombL.ar(windNoise, 0.1, (freq * 2.2).reciprocal, tube.linlin(0, 1, 0.1, 0.6));
    tubeSig = combs * tube * 0.6;

    // Wire singing - high pitched resonance
    wireSig = Resonz.ar(windNoise, freq * 4 * LFNoise2.kr(0.3).range(0.9, 1.1), 0.01);
    wireSig = wireSig * wire * 10;

    // Rattling loose parts
    rattSig = Dust.ar(ratt.linexp(0, 1, 1, 20) * gustMod) * 0.3;
    rattSig = Ringz.ar(rattSig, freq * LFNoise0.kr(5).range(2, 6), 0.05);
    rattSig = rattSig * ratt;

    // Mix
    sig = windNoise + tubeSig + wireSig + rattSig;

    // Cold wind - add high frequency
    sig = sig + (HPF.ar(WhiteNoise.ar(1), 4000) * cold * gustMod * 0.15);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_duga_steel loaded".postln;
