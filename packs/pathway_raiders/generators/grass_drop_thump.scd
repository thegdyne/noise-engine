// pathway_raiders/grass_drop_thump.scd
// Pathway Raiders — grass_drop_thump
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 SPD: speed / excitement
// P2 BRK: brake/skid grit
// P3 AIR: open air / distance
// P4 HID: hide/seek occlusion
// P5 SUN: day mood (bright ↔ dusk)

SynthDef(\forge_pathway_raiders_grass_drop_thump, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                    filterTypeBus, envEnabledBus, envSourceBus=0,
                                    clockRateBus, clockTrigBus,
                                    midiTrigBus=0, slotIndex=0,
                                    customBus0, customBus1, customBus2, customBus3, customBus4,
                                    portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var spd, brk, air, hid, sun;
    var a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r, s;

    // Theme params
    spd = In.kr(customBus0).clip(0, 1);
    brk = In.kr(customBus1).clip(0, 1);
    air = In.kr(customBus2).clip(0, 1);
    hid = In.kr(customBus3).clip(0, 1);
    sun = In.kr(customBus4).clip(0, 1);

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

// drop events: sparse but not silent
a = Dust.ar(0.35 + (spd * 2.5));
b = Decay2.ar(a, 0.001, 0.06 + (spd * 0.12));

// impact exciter
c = WhiteNoise.ar(0.35) * b;
c = HPF.ar(c, 120);

// membrane body (short)
d = BPF.ar(c, (80 + (spd * 240)).clip(60, 600), 0.35) * 2.0;
e = (d * (1 + (brk * 2.0))).tanh;

// grass hiss tail
f = Decay2.ar(a, 0.01, 0.25 + (air * 0.75));
g = HPF.ar(PinkNoise.ar(0.06), 700) * f;

// hide = muffled
h = LPF.ar(e + g, (9000 - (hid * 7500)).clip(900, 9000)) * (1 - (hid * 0.6)).clip(0.2, 1);

// always-on ambient bed
i = HPF.ar(PinkNoise.ar(0.15), 500) + BrownNoise.ar(0.12);
sig = (h * 0.9) + (i * 0.8);

    // MANDATORY output chain (this order):
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.90);
sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_pathway_raiders loaded".postln;
