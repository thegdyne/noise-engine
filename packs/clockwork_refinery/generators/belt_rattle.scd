// clockwork_refinery/belt_rattle.scd
// Clockwork Refinery — belt_rattle
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 DRF: drift / instability
// P2 GRT: grit / saturation
// P3 SPC: space / chamber
// P4 DRP: dropout / missing teeth
// P5 MOD: mode / coarse↔fine morph

SynthDef(\forge_clockwork_refinery_belt_rattle, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
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

a = WhiteNoise.ar(0.20);
b = (2 + (mod * 14)).clip(2, 20);
c = (b * (1 + (LFNoise0.kr(2).range(-0.15, 0.15) * drf))).clip(0.5, 40);
d = LFPulse.kr(c, 0, 0.1 + (mod * 0.5)).lag(0.002);
e = (d > drp).asInteger; // dropout as missing pulses
f = a * d * e;

g = BPF.ar(f, (freq * (1 + (drf * 0.15))).clip(60, 12000), 0.2 + (mod * 0.4)) * (4 + (mod * 2));
h = CombC.ar(g, 0.25, (0.008 + (mod * 0.04)).clip(0.008, 0.2), 0.4 + (spc * 1.8));

sig = ((g * 0.8) + (h * 0.8));
sig = (sig * (1 + (grt * 4))).tanh;

    // MANDATORY output chain (this order):
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_clockwork_refinery loaded".postln;
