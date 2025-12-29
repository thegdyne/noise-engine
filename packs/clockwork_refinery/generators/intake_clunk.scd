// clockwork_refinery/intake_clunk.scd
// Clockwork Refinery — intake_clunk
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 DRF: drift / instability
// P2 GRT: grit / saturation
// P3 SPC: space / chamber
// P4 DRP: dropout / missing teeth
// P5 MOD: mode / coarse↔fine morph

SynthDef(\forge_clockwork_refinery_intake_clunk, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
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

// Internal hit source (hybrid initial + continuous)
a = (Impulse.ar(0) + Dust.ar(0.5 + (mod * 6))).clip2(1); // trigger
b = Decay2.ar(a, 0.001, 0.06 + (mod * 0.18));
c = WhiteNoise.ar(0.35) * b;

// Body modes (avoid .sum on non-array by making explicit array)
d = (freq * [0.75, 1.0, 1.33]).clip(30, 8000);
e = Ringz.ar(c, d * (1 + (LFNoise1.kr(0.15).range(-0.02, 0.02) * drf)), 0.12 + (mod * 0.25)).sum;

// Grit + dropout
f = e * (1 - (drp * 0.85));
g = (f * (1 + (grt * 6))).tanh;

// Space (duct bloom)
h = CombC.ar(g, 0.35, (0.015 + (spc * 0.22)).clip(0.015, 0.33), 1.2 + (spc * 2.0));
sig = (g * 0.7) + (h * 0.6) + (PinkNoise.ar(0.006) * (1 - drp));

    // MANDATORY output chain (this order):
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_clockwork_refinery loaded".postln;
