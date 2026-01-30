// cleanroom_shift/ballast_white — Lightweight end-stage generator
// cleanroom_shift/ballast_white.scd
// Cleanroom Shift — ballast_white
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 DRF: drift / fatigue / micro instability
// P2 GRT: grit / switching hash
// P3 SPC: space / duct bloom
// P4 DRP: dropout / interlock gating
// P5 SHF: shift state (timeless cycle intensity)

SynthDef(\forge_cleanroom_shift_ballast_white, { |out, freqBus, customBus0|

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

a = (50 + (shf * 30));
b = SinOsc.ar(a) * 0.10;
c = SinOsc.ar(a * (2.01 + (drf * 0.08))) * 0.06;
d = SinOsc.ar(a * (3.97 + (drf * 0.12))) * 0.04;
e = b + c + d;

f = SinOsc.ar((freq * (6 + (shf * 24))).clip(120, 12000));
g = (e * f) * (0.8 + (grt * 2.2));

h = Dust.ar(0.3 + (shf * 2.5)) * (1 - (drp * 0.8));
i = Decay2.ar(h, 0.001, 0.015 + (shf * 0.05));
j = WhiteNoise.ar(0.30) * i;
k = BPF.ar(j, (3000 + (shf * 9000)).clip(1000, 12000), 0.2);

l = (g + (k * 0.7));
m = (l * (1 + (grt * 3))).tanh;
n = CombC.ar(m, 0.20, (0.01 + (spc * 0.08)).clip(0.01, 0.12), 0.5 + (spc * 1.2));
sig = (m * 0.85) + (n * 0.35) + PinkNoise.ar(0.002);

    // MANDATORY output chain (this order):
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_cleanroom_shift loaded".postln;
