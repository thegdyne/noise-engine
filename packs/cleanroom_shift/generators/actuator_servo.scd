// cleanroom_shift/actuator_servo — Lightweight end-stage generator
// cleanroom_shift/actuator_servo.scd
// Cleanroom Shift — actuator_servo
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 DRF: drift / fatigue / micro instability
// P2 GRT: grit / switching hash
// P3 SPC: space / duct bloom
// P4 DRP: dropout / interlock gating
// P5 SHF: shift state (timeless cycle intensity)

SynthDef(\forge_cleanroom_shift_actuator_servo, { |out, freqBus, customBus0|

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

a = (0.06 + (shf * 0.35)).clip(0.06, 0.6);
b = LFNoise1.kr(a).range(-1, 1) * (0.02 + (drf * 0.08));
c = (freq * (8 + (shf * 24))).clip(80, 14000);
d = SinOsc.ar(c * (1 + b)) * 0.25;

e = LFNoise0.kr(4 + (shf * 28)).range(-1, 1);
f = (e * (0.01 + (drf * 0.06)));
g = SinOsc.ar(c * (1 + f)) * 0.22;

h = HPF.ar(WhiteNoise.ar(0.08), 2500) * (0.4 + (grt * 1.2));

i = d + g + h;
j = LFNoise0.kr(0.8 + (shf * 5)).range(0, 1);
k = (j - drp).clip(0.2, 1);
l = i * k;

m = (l * (1 + (grt * 3))).tanh;
n = CombC.ar(m, 0.22, (0.01 + (spc * 0.12)).clip(0.01, 0.16), 0.5 + (spc * 1.4));
sig = (m * 0.85) + (n * 0.35) + PinkNoise.ar(0.002);

    // MANDATORY output chain (this order):
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_cleanroom_shift loaded".postln;
