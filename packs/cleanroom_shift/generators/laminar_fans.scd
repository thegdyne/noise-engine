// cleanroom_shift/laminar_fans — Lightweight end-stage generator
// cleanroom_shift/laminar_fans.scd
// Cleanroom Shift -- laminar_fans
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 DRF: drift / fatigue / micro instability
// P2 GRT: grit / switching hash
// P3 SPC: space / duct bloom
// P4 DRP: dropout / interlock gating
// P5 SHF: shift state (timeless cycle intensity)

SynthDef(\forge_cleanroom_shift_laminar_fans, { |out, freqBus, customBus0|

    var sig, trig, freq;
    var p = In.kr(customBus0, 5);
    var drf, grt, spc, drp, shf;
    var a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q;

    drf = p[0].clip(0, 1);
    grt = p[1].clip(0, 1);
    spc = p[2].clip(0, 1);
    drp = p[3].clip(0, 1);
    shf = p[4].clip(0, 1);

    freq = In.kr(freqBus);

a = PinkNoise.ar(0.45) + BrownNoise.ar(0.18);
a = HPF.ar(a, 80);

b = (0.03 + (shf * 0.12)).clip(0.03, 0.2);
c = LFNoise1.kr(b).range(0.6, 1.4);

d = (filterFreq * (0.5 + (c * 0.7))).clip(120, 9000);
e = Resonz.ar(a, d, (0.03 + (rq * 0.06)).clip(0.02, 0.25)) * 8;
f = Resonz.ar(a, (d * 1.6).clip(120, 12000), (0.02 + (rq * 0.05)).clip(0.02, 0.2)) * 6;

g = LFNoise0.kr(0.6 + (shf * 3)).range(0, 1);
h = (g - drp).clip(0.15, 1);
i = (e + f) * h;

j = (i * (1 + (grt * 2.5))).tanh;
k = CombC.ar(j, 0.30, (0.02 + (spc * 0.16)).clip(0.02, 0.22), 1.4 + (spc * 2.0));
sig = (j * 0.95) + (k * 0.45) + PinkNoise.ar(0.012);
sig = sig * (2.5 + (shf * 1.5));   // louder, "shift intensity"
sig = (sig * 1.2).tanh;

    // MANDATORY output chain (this order):
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_cleanroom_shift loaded".postln;
