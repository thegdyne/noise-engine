// cleanroom_shift/tester_jig — Lightweight end-stage generator
// cleanroom_shift/tester_jig.scd
// Cleanroom Shift — tester_jig
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 DRF: drift / fatigue / micro instability
// P2 GRT: grit / switching hash
// P3 SPC: space / duct bloom
// P4 DRP: dropout / interlock gating
// P5 SHF: shift state (timeless cycle intensity)

SynthDef(\forge_cleanroom_shift_tester_jig, { |out, freqBus, customBus0|

    var sig, trig, freq;
    var p = In.kr(customBus0, 5);
    var drf, grt, spc, drp, shf;
    var a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, q, pre;

    drf = p[0].clip(0, 1);
    grt = p[1].clip(0, 1);
    spc = p[2].clip(0, 1);
    drp = p[3].clip(0, 1);
    shf = p[4].clip(0, 1);

    freq = In.kr(freqBus);

a = Dust.kr(0.12 + (shf * 1.2));
b = Stepper.kr(a, 0, 0, 3, 1);
c = b / 3;

e = Decay2.ar(K2A.ar(a), 0.001, 0.05 + (shf * 0.15));
f = WhiteNoise.ar(0.35) * e;
f = HPF.ar(f, 180);
g = BPF.ar(f, (freq * 3).clip(200, 8000), 0.25);
g = (g * 2.0).tanh;

h = (c + (LFNoise1.kr(0.08).range(-0.1, 0.1) * drf)).clip(0, 1);
i = SinOsc.ar(freq * (6 + (shf * 18))).clip2(1);
j = LFTri.ar(freq * (6 + (shf * 18)));
k = Saw.ar(freq * (6 + (shf * 18)));
l = SelectX.ar(h * 2, [j, k, i]) * 0.18;

m = Dust.ar(0.25 + (shf * 2.0));
n = Decay2.ar(m, 0.001, 0.02);
o = SinOsc.ar((1600 + (shf * 1800)).clip(600, 5000)) * n * 0.18;

pre = LFNoise0.kr(0.7 + (shf * 4)).range(0, 1);
q = (pre - drp).clip(0.15, 1);

sig = ((g * 0.55) + (l * 0.9) + (o * 0.6)) * q;
sig = sig * (1 - (Decay2.kr(a, 0.001, 0.12) * 0.35));
sig = (sig * (1 + (grt * 3))).tanh;

// sterile smear (no runaway)
sig = AllpassC.ar(sig, 0.08, (0.005 + (spc * 0.02)).clip(0.005, 0.03), 0.12);
sig = (sig * 0.8).tanh;

sig = sig + PinkNoise.ar(0.008);

    // MANDATORY output chain (this order):
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_cleanroom_shift loaded".postln;
