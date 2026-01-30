// pathway_raiders/chain_freewheel — Lightweight end-stage generator
// pathway_raiders/chain_freewheel.scd
// Pathway Raiders — chain_freewheel
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 SPD: speed / excitement
// P2 BRK: brake/skid grit
// P3 AIR: open air / distance
// P4 HID: hide/seek occlusion
// P5 SUN: day mood (bright ↔ dusk)

SynthDef(\forge_pathway_raiders_chain_freewheel, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var spd, brk, air, hid, sun;
    var a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r, s;

    spd = p[0].clip(0, 1);
    brk = p[1].clip(0, 1);
    air = p[2].clip(0, 1);
    hid = p[3].clip(0, 1);
    sun = p[4].clip(0, 1);

    freq = In.kr(freqBus);

// base chain chatter: narrow moving peaks
a = HPF.ar(WhiteNoise.ar(0.14), 120);
b = (8 + (spd * 30)).clip(8, 38);
c = LFNoise1.kr(0.2 + (spd * 1.5)).range(0.7, 1.4);
d = (freq * (6 + (spd * 18)) * c).clip(120, 12000);

e = BPF.ar(a, d, 0.22) * 2.2;
f = BPF.ar(a, (d * 1.6).clip(120, 16000), 0.18) * 1.6;
g = (e + f);

// chain slap ticks
h = Dust.ar(1.2 + (spd * 10));
i = Decay2.ar(h, 0.001, 0.010 + (spd * 0.03));
j = HPF.ar(WhiteNoise.ar(0.30), 2500) * i;

// brake = skid burst
k = Dust.ar(0.12 + (brk * 1.2));
l = Decay2.ar(k, 0.001, 0.06 + (brk * 0.10));
m = BPF.ar(WhiteNoise.ar(0.25), (1500 + (brk * 6000)).clip(800, 9000), 0.35) * l;

// always-on bed to avoid SPARSE
n = HPF.ar(PinkNoise.ar(0.15), 600) + BrownNoise.ar(0.12);

// occlusion
o = (1 - (hid * 0.7)).clip(0.2, 1);
p = LPF.ar((g + j + m) * o, (8000 - (hid * 6500)).clip(900, 9000));

// day mood tilt
q = XFade2.ar(LPF.ar(p, 3500), p, (sun * 2 - 1));
sig = (q * 0.85) + (n * 0.65);

    // MANDATORY output chain (this order):
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_pathway_raiders loaded".postln;
