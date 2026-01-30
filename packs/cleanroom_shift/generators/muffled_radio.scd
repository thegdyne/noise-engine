// cleanroom_shift/muffled_radio — Lightweight end-stage generator
// cleanroom_shift/muffled_radio.scd
// Cleanroom Shift — muffled_radio
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 DRF: drift / fatigue / micro instability
// P2 GRT: grit / switching hash
// P3 SPC: space / duct bloom
// P4 DRP: dropout / interlock gating
// P5 SHF: shift state (timeless cycle intensity)

SynthDef(\forge_cleanroom_shift_muffled_radio, { |out, freqBus, customBus0|

    var sig, trig, freq;
    var p = In.kr(customBus0, 5);
    var drf, grt, spc, drp, shf;
    var a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, q;

    drf = p[0].clip(0, 1);
    grt = p[1].clip(0, 1);
    spc = p[2].clip(0, 1);
    drp = p[3].clip(0, 1);
    shf = p[4].clip(0, 1);

    freq = In.kr(freqBus);

a = (3 + (shf * 30)).clip(3, 36);
b = (0.03 + (shf * 0.10)).clip(0.03, 0.16);
c = Dust.ar(a * (1 - (drp * 0.6)));

d = Mix.fill(7, { |i|
    var ff, pp, ww;
    ww = (0.18 + (i * 0.07)).clip(0.18, 0.6);
    ff = (freq * (0.75 + (i * ww))).clip(80, 6000);
    pp = LFNoise1.kr(0.12 + (drf * 0.5)).range(-1, 1);
    GrainSin.ar(2, c, b, ff, pp, -1, 512, 0.10)
});

e = BPF.ar(d, (900 + (shf * 1800)).clip(300, 3500), 0.4);
f = (e * (1 + (grt * 2.5))).tanh;

g = LFNoise0.kr(0.8 + (shf * 5)).range(0, 1);
h = (1 - ((g * drp) * 0.8)).clip(0.2, 1);

i = CombC.ar(f, 0.35, (0.02 + (spc * 0.22)).clip(0.02, 0.28), 1.0 + (spc * 2.6));

sig = ((f * 0.85) + (i * 0.35)) * h + PinkNoise.ar(0.003);

    // MANDATORY output chain (this order):
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_cleanroom_shift loaded".postln;
