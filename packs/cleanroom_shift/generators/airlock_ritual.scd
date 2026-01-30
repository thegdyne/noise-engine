// cleanroom_shift/airlock_ritual — Lightweight end-stage generator
// cleanroom_shift/airlock_ritual.scd
// Cleanroom Shift — airlock_ritual
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 DRF: drift / fatigue / micro instability
// P2 GRT: grit / switching hash
// P3 SPC: space / duct bloom
// P4 DRP: dropout / interlock gating
// P5 SHF: shift state (timeless cycle intensity)

SynthDef(\forge_cleanroom_shift_airlock_ritual, { |out, freqBus, customBus0|

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

a = (Impulse.ar(0) + Dust.ar(0.35 + (shf * 2.8)));
b = Decay2.ar(a, 0.001, 0.08 + (shf * 0.22));
c = WhiteNoise.ar(0.35) * b;

d = (freq * [0.7, 1.0, 1.28]).clip(40, 6000);
e = Ringz.ar(c, d * (1 + (LFNoise1.kr(0.15).range(-0.02, 0.02) * drf)), 0.10 + (shf * 0.35)).sum;

f = Decay2.ar(a, 0.02, 0.6 + (spc * 1.8));
g = HPF.ar(PinkNoise.ar(0.10), 200) * f;
h = BPF.ar(g, (1000 + (shf * 2500)).clip(400, 4000), 0.3);

i = LFNoise0.kr(1.2 + (shf * 5)).range(0, 1);
j = (i - drp).clip(0, 1);
k = ((e * 0.9) + (h * 0.8)) * (0.25 + (j * 0.75));

l = (k * (1 + (grt * 5))).tanh;
m = CombC.ar(l, 0.30, (0.02 + (spc * 0.20)).clip(0.02, 0.25), 0.9 + (spc * 2.2));
sig = (l * 0.85) + (m * 0.45) + PinkNoise.ar(0.003);

    // MANDATORY output chain (this order):
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_cleanroom_shift loaded".postln;
