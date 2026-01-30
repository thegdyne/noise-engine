// pathway_raiders/grass_drop_thump — Lightweight end-stage generator
// pathway_raiders/grass_drop_thump.scd
// Pathway Raiders — grass_drop_thump
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 SPD: speed / excitement
// P2 BRK: brake/skid grit
// P3 AIR: open air / distance
// P4 HID: hide/seek occlusion
// P5 SUN: day mood (bright ↔ dusk)

SynthDef(\forge_pathway_raiders_grass_drop_thump, { |out, freqBus, customBus0|

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
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_pathway_raiders loaded".postln;
