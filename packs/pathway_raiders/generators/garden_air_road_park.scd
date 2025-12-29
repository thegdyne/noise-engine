// pathway_raiders/garden_air_road_park.scd
// Pathway Raiders — garden_air_road_park
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 SPD: speed / excitement
// P2 BRK: brake/skid grit
// P3 AIR: open air / distance
// P4 HID: hide/seek occlusion
// P5 SUN: day mood (bright ↔ dusk)

SynthDef(\forge_pathway_raiders_garden_air_road_park, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
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

// wind bed: moving peaks
a = PinkNoise.ar(0.12) + (BrownNoise.ar(0.07));
b = HPF.ar(a, 60);
c = LFNoise1.kr(0.04 + (air * 0.16)).range(0.6, 1.5);
d = (filterFreq * (0.35 + (c * 0.85))).clip(120, 8500);
e = Resonz.ar(b, d, 0.08) * 3.5;

// distant road: low band rumble (very low)
f = LPF.ar(BrownNoise.ar(0.06), 140 + (air * 140));
g = (f * 0.4).tanh;

// park bed: faint mid noise
h = HPF.ar(PinkNoise.ar(0.02), 450);

// hide: occlusion + dip
i = (1 - (hid * 0.6)).clip(0.25, 1);
j = LPF.ar((e + g + h) * i, (9000 - (hid * 7500)).clip(900, 9000));

// sun tilt: brighter afternoon = more HF
k = HPF.ar(j, (200 + (sun * 700)).clip(200, 900));
l = AllpassC.ar(k, 0.10, (0.006 + (air * 0.03)).clip(0.006, 0.035), 0.12);

sig = (k * 0.85) + (l * (0.10 + (air * 0.25))) + HPF.ar(PinkNoise.ar(0.15), 600) + BrownNoise.ar(0.12);

    // MANDATORY output chain (this order):
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_pathway_raiders loaded".postln;
