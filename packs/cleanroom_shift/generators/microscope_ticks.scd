// cleanroom_shift/microscope_ticks — Lightweight end-stage generator
// cleanroom_shift/microscope_ticks.scd
// Cleanroom Shift — microscope_ticks
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 DRF: drift / fatigue / micro instability
// P2 GRT: grit / switching hash
// P3 SPC: space / duct bloom
// P4 DRP: dropout / interlock gating
// P5 SHF: shift state (timeless cycle intensity)

SynthDef(\forge_cleanroom_shift_microscope_ticks, { |out, freqBus, customBus0|

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

a = Dust.ar(1.2 + (shf * 12)) * (1 - (drp * 0.75));
b = Decay2.ar(a, 0.001, 0.012 + (shf * 0.05));
c = WhiteNoise.ar(0.22) * b;

d = (freq * [2.0, 2.7, 3.9]).clip(200, 12000);
e = Ringz.ar(c, d * (1 + (LFNoise1.kr(0.25).range(-0.01, 0.01) * drf)), 0.04 + (shf * 0.14)).sum;

f = HPF.ar(PinkNoise.ar(0.015), 500);
g = HPF.ar(e, 250);
h = (g * (1 + (grt * 4))).tanh;

i = CombC.ar(h, 0.12, (0.008 + (spc * 0.06)).clip(0.008, 0.09), 0.25 + (spc * 0.6));
sig = (h * 0.9) + (i * 0.35) + (f * 0.35);

    // MANDATORY output chain (this order):
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_cleanroom_shift loaded".postln;
