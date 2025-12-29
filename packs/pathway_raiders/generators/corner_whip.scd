// pathway_raiders/corner_whip.scd
// Pathway Raiders — corner_whip
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 SPD: speed / excitement
// P2 BRK: brake/skid grit
// P3 AIR: open air / distance
// P4 HID: hide/seek occlusion
// P5 SUN: day mood (bright ↔ dusk)

SynthDef(\forge_pathway_raiders_corner_whip, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
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

// scrub events: more at higher speed
a = Dust.ar(0.25 + (spd * 3.0));
b = Decay2.ar(a, 0.001, 0.03 + (spd * 0.06));
c = (freq * (10 + (spd * 18))).clip(120, 14000);

// squeal oscillator + ring mod edge
d = SinOsc.ar(c) * b * 0.35;
e = SinOsc.ar((c * (2.0 + (brk * 2.0))).clip(120, 16000));
f = (d * e) * (0.8 + (brk * 2.5));
g = (f * 1.6).tanh;

// micro tyre hiss bed
h = HPF.ar(WhiteNoise.ar(0.03), 2200);

// hide occlusion + air smear
i = LPF.ar(g + h, (9000 - (hid * 7000)).clip(1200, 9000)) * (1 - (hid * 0.55));
j = AllpassC.ar(i, 0.07, (0.004 + (air * 0.025)).clip(0.004, 0.03), 0.10);

// sun tilt (dusk warmer = less HF)
k = LPF.ar(i + (j * 0.25), (3500 + (sun * 4500)).clip(2500, 8000));
sig = k + HPF.ar(PinkNoise.ar(0.15), 900) + BrownNoise.ar(0.12);

    // MANDATORY output chain (this order):
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.90);
sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_pathway_raiders loaded".postln;
