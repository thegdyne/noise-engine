// pathway_raiders/shed_tool_rattle.scd
// Pathway Raiders — shed_tool_rattle
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 SPD: speed / excitement
// P2 BRK: brake/skid grit
// P3 AIR: open air / distance
// P4 HID: hide/seek occlusion
// P5 SUN: day mood (bright ↔ dusk)

SynthDef(\forge_pathway_raiders_shed_tool_rattle, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
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

// drawer clacks
a = Dust.ar(0.25 + (spd * 2.0));
b = Decay2.ar(a, 0.001, 0.05 + (spd * 0.10));
c = WhiteNoise.ar(0.35) * b;
d = BPF.ar(c, (500 + (spd * 1800)).clip(200, 4000), 0.25) * 2.2;

// loose tool rattle: clustered band peaks, short and gritty
e = Dust.ar(0.7 + (spd * 6.0));
f = Decay2.ar(e, 0.001, 0.018 + (spd * 0.05));
g = HPF.ar(WhiteNoise.ar(0.20), 900) * f;
h = BPF.ar(g, (1200 + (LFNoise1.kr(0.6).range(-400, 1200))).clip(800, 4500), 0.35) * 2.0;

// brake = harsher metal edge
i = (d + h) * (1 + (brk * 3.0));
i = (i * 0.9).tanh;

// hide = muffled in shed
j = LPF.ar(i, (8000 - (hid * 6500)).clip(900, 9000)) * (1 - (hid * 0.5));

// tiny air reflections + constant bed (dusty shed air)
k = AllpassC.ar(j, 0.08, (0.004 + (air * 0.02)).clip(0.004, 0.03), 0.10);
l = HPF.ar(PinkNoise.ar(0.15), 700) + BrownNoise.ar(0.12);

sig = (j * 0.85) + (k * (0.10 + (air * 0.25))) + (l * 0.8);

    // MANDATORY output chain (this order):
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.90);
sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_pathway_raiders loaded".postln;
