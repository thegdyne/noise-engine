// clockwork_refinery/gear_grind.scd
// Clockwork Refinery — gear_grind
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 DRF: drift / instability
// P2 GRT: grit / saturation
// P3 SPC: space / chamber
// P4 DRP: dropout / missing teeth
// P5 MOD: mode / coarse↔fine morph

SynthDef(\forge_clockwork_refinery_gear_grind, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
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

a = PinkNoise.ar(0.25) + BrownNoise.ar(0.10);
b = (0.3 + (drf * 2.2)).clip(0.3, 3.0);
c = LFNoise1.kr(b).exprange(120, 4200);
d = Resonz.ar(a, c, (0.05 + (mod * 0.25)).clip(0.05, 0.8)) * (3 + (mod * 4));

// Tooth-drop gating (continuous but with missing frames)
e = LFNoise0.kr(6 + (mod * 22)).range(0, 1);
f = (e > drp).asInteger;          // boolean safety
g = d * f;

// Grit + space
h = (g * (1 + (grt * 5))).tanh;
i = CombC.ar(h, 0.30, (0.02 + (spc * 0.18)).clip(0.02, 0.25), 0.8 + (spc * 2.4));
sig = (h * 0.85) + (i * 0.45);

    // MANDATORY output chain (this order):
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_clockwork_refinery loaded".postln;
