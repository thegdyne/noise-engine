// pathway_raiders/corner_whip — Lightweight end-stage generator
// pathway_raiders/corner_whip.scd
// Pathway Raiders — corner_whip
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 SPD: speed / excitement
// P2 BRK: brake/skid grit
// P3 AIR: open air / distance
// P4 HID: hide/seek occlusion
// P5 SUN: day mood (bright ↔ dusk)

SynthDef(\forge_pathway_raiders_corner_whip, { |out, freqBus, customBus0|

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
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_pathway_raiders loaded".postln;
