// clockwork_refinery/output_haze.scd
// Clockwork Refinery — output_haze
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 DRF: drift / instability
// P2 GRT: grit / saturation
// P3 SPC: space / chamber
// P4 DRP: dropout / missing teeth
// P5 MOD: mode / coarse↔fine morph

SynthDef(\forge_clockwork_refinery_output_haze, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                    filterTypeBus, envEnabledBus, envSourceBus=0,
                                    clockRateBus, clockTrigBus,
                                    midiTrigBus=0, slotIndex=0,
                                    customBus0, customBus1, customBus2, customBus3, customBus4,
                                    portamentoBus|

    var sig, trig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var drf, grt, spc, drp, mod;
    var a, b, c, d, e, f, g, h, i, j, k, l, m, n;

    // Theme params
    drf = In.kr(customBus0).clip(0, 1);
    grt = In.kr(customBus1).clip(0, 1);
    spc = In.kr(customBus2).clip(0, 1);
    drp = In.kr(customBus3).clip(0, 1);
    mod = In.kr(customBus4).clip(0, 1);

    // Standard reads
    freq = In.kr(freqBus);
    portamento = In.kr(portamentoBus);
    freq = Lag.kr(freq, portamento.linexp(0, 1, 0.001, 0.5)).clip(20, 20000);
    filterFreq = In.kr(cutoffBus).clip(20, 18000);
    rq = In.kr(resBus).clip(0.05, 2);
    attack = In.kr(attackBus).clip(0, 1);
    decay = In.kr(decayBus).clip(0, 1);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    ampVal = In.kr(~params[\amplitude]);

a = (4 + (mod * 36)).clip(4, 40); // density-ish
b = (0.02 + (mod * 0.14)).clip(0.02, 0.18); // dur
c = Dust.ar(a * (1 - (drp * 0.7)));

// 7-voice cloud (integer literal count required)
d = Mix.fill(7, { |i|
    var ff, pp;
    ff = (freq * (0.5 + (i * 0.18))).clip(40, 12000);
    pp = LFNoise1.kr(0.2 + (drf * 0.6)).range(-1, 1);
    // args: numCh, trig, dur, freq, pan, envbufnum, maxGrains, mul
    GrainSin.ar(2, c, b, ff, pp, -1, 512, 0.12)
});

e = (d * (1 + (grt * 6))).tanh;

// Space smear
f = CombC.ar(e, 0.35, (0.02 + (spc * 0.25)).clip(0.02, 0.3), 1.2 + (spc * 3.0));
sig = (e * 0.8) + (f * 0.55) + (PinkNoise.ar(0.004) * (1 - drp));
sig = sig + PinkNoise.ar(0.002);

    // MANDATORY output chain (this order):
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_clockwork_refinery loaded".postln;
