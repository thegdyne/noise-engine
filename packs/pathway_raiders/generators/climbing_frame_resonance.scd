// pathway_raiders/climbing_frame_resonance.scd
// Pathway Raiders — climbing_frame_resonance
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 SPD: speed / excitement
// P2 BRK: brake/skid grit
// P3 AIR: open air / distance
// P4 HID: hide/seek occlusion
// P5 SUN: day mood (bright ↔ dusk)

SynthDef(\forge_pathway_raiders_climbing_frame_resonance, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
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

// ladder ticks
a = Dust.ar(0.8 + (spd * 9.0));
b = Decay2.ar(a, 0.001, 0.012 + (spd * 0.05));
c = WhiteNoise.ar(0.22) * b;

// modal cluster (non-musical)
d = (freq * [1.8, 2.6, 3.3]).clip(200, 12000);
e = BPF.ar(c, d, 0.12).sum * 3.0;

// handrail knocks (bigger)
f = Dust.ar(0.18 + (spd * 1.4));
g = Decay2.ar(f, 0.001, 0.08 + (spd * 0.10));
h = BPF.ar(WhiteNoise.ar(0.28) * g, (400 + (spd * 900)).clip(200, 2500), 0.25) * 2.0;

// brake adds metallic bite
i = (e + h) * (1 + (brk * 2.5));
i = (i * 0.8).tanh;

// air = tiny sterile reflections (allpass)
j = AllpassC.ar(i, 0.10, (0.006 + (air * 0.03)).clip(0.006, 0.035), 0.14);

// hide occlusion
k = LPF.ar(i + (j * 0.35), (8000 - (hid * 6500)).clip(900, 9000)) * (1 - (hid * 0.55));

// constant low bed (garden air)
l = HPF.ar(PinkNoise.ar(0.15), 650) + BrownNoise.ar(0.12);
sig = (k * 0.85) + (l * 0.8);

    // MANDATORY output chain (this order):
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_pathway_raiders loaded".postln;
