// pathway_raiders/patio_grout_bumps.scd
// Pathway Raiders — patio_grout_bumps
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 SPD: speed / excitement
// P2 BRK: brake/skid grit
// P3 AIR: open air / distance
// P4 HID: hide/seek occlusion
// P5 SUN: day mood (bright ↔ dusk)

SynthDef(\forge_pathway_raiders_patio_grout_bumps, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
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

// micro bump train (grout lines) + occasional double-bump
a = (3 + (spd * 24)).clip(3, 30);                 // rate base
b = LFPulse.kr(a, 0, (0.08 + (spd * 0.20)).clip(0.08, 0.35));
c = Dust.kr(0.6 + (spd * 3.0));
d = (b + (c * 0.25)).clip(0, 1);

// double-bump probability
e = Dust.kr(0.15 + (spd * 0.9));
f = Decay2.kr(e, 0.001, 0.06);
d = (d + (f * 0.5)).clip(0, 1);

// bump exciter
g = WhiteNoise.ar(0.20) * K2A.ar(d);
h = BPF.ar(g, (800 + (spd * 3200)).clip(300, 6500), 0.35);
i = HPF.ar(PinkNoise.ar(0.03), 500); // guaranteed bed

// brake grit edge
j = (h * (1 + (brk * 5))).tanh;

// occlusion (hide): dip + LPF
k = (1 - (hid * 0.65)).clip(0.25, 1);
l = LPF.ar(j, (6000 - (hid * 4500)).clip(800, 8000)) * k;

// tiny open-air smear
m = AllpassC.ar(l, 0.06, (0.004 + (air * 0.02)).clip(0.004, 0.03), 0.08);
sig = (l * 0.85) + (m * (0.15 + (air * 0.25))) + (i * 0.55);

    // MANDATORY output chain (this order):
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_pathway_raiders loaded".postln;
