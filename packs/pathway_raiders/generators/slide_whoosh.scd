// pathway_raiders/slide_whoosh — Lightweight end-stage generator
// pathway_raiders/slide_whoosh.scd
// Pathway Raiders — slide_whoosh
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 SPD: speed / excitement
// P2 BRK: brake/skid grit
// P3 AIR: open air / distance
// P4 HID: hide/seek occlusion
// P5 SUN: day mood (bright ↔ dusk)

SynthDef(\forge_pathway_raiders_slide_whoosh, { |out, freqBus, customBus0|

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

// whoosh swells
a = Dust.kr(0.35 + (spd * 2.0));
b = Decay2.kr(a, 0.02, 0.18 + (spd * 0.45));
c = HPF.ar(WhiteNoise.ar(0.10), 600) * K2A.ar(b);

// bump pulses on the slide
d = Dust.ar(0.8 + (spd * 10.0));
e = Decay2.ar(d, 0.001, 0.012 + (spd * 0.04));
f = BPF.ar(WhiteNoise.ar(0.24) * e, (1200 + (spd * 3500)).clip(600, 7000), 0.35);

// day mood tilt: dusk softer
g = LPF.ar(c + f, (3500 + (sun * 5500)).clip(2000, 9000));

// hide occlusion (behind bushes)
h = LPF.ar(g, (9000 - (hid * 7500)).clip(900, 9000)) * (1 - (hid * 0.6)).clip(0.25, 1);

// airy smear
i = AllpassC.ar(h, 0.10, (0.006 + (air * 0.03)).clip(0.006, 0.035), 0.12);

// always-on bed
j = HPF.ar(PinkNoise.ar(0.15), 700) + BrownNoise.ar(0.12);
sig = (h * 0.85) + (i * (0.10 + (air * 0.25))) + (j * 0.8);

    // MANDATORY output chain (this order):
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_pathway_raiders loaded".postln;
