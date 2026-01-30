// pathway_raiders/garden_air_road_park — Lightweight end-stage generator
// pathway_raiders/garden_air_road_park.scd
// Pathway Raiders — garden_air_road_park
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 SPD: speed / excitement
// P2 BRK: brake/skid grit
// P3 AIR: open air / distance
// P4 HID: hide/seek occlusion
// P5 SUN: day mood (bright ↔ dusk)

SynthDef(\forge_pathway_raiders_garden_air_road_park, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var spd, brk, air, hid, sun;
    var a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, q, r, s;

    spd = p[0].clip(0, 1);
    brk = p[1].clip(0, 1);
    air = p[2].clip(0, 1);
    hid = p[3].clip(0, 1);
    sun = p[4].clip(0, 1);

    freq = In.kr(freqBus);

// wind bed: moving peaks
a = PinkNoise.ar(0.12) + (BrownNoise.ar(0.07));
b = HPF.ar(a, 60);
c = LFNoise1.kr(0.04 + (air * 0.16)).range(0.6, 1.5);
d = (freq * (0.35 + (c * 0.85))).clip(120, 8500);
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
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_pathway_raiders loaded".postln;
