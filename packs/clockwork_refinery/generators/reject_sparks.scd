// clockwork_refinery/reject_sparks — Lightweight end-stage generator
// clockwork_refinery/reject_sparks.scd
// Clockwork Refinery — reject_sparks
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 DRF: drift / instability
// P2 GRT: grit / saturation
// P3 SPC: space / chamber
// P4 DRP: dropout / missing teeth
// P5 MOD: mode / coarse↔fine morph

SynthDef(\forge_clockwork_refinery_reject_sparks, { |out, freqBus, customBus0|

    var sig, trig, freq;
    var p = In.kr(customBus0, 5);
    var drf, grt, spc, drp, mod;
    var a, b, c, d, e, f, g, h, i, j, k, l, m, n;

    drf = p[0].clip(0, 1);
    grt = p[1].clip(0, 1);
    spc = p[2].clip(0, 1);
    drp = p[3].clip(0, 1);
    mod = p[4].clip(0, 1);

    freq = In.kr(freqBus);

a = Dust.ar(2 + (mod * 28)) * (1 - (drp * 0.85));
b = Decay2.ar(a, 0.001, 0.02 + (mod * 0.08));
c = WhiteNoise.ar(0.25) * b;

d = (freq * (2 + (mod * 10))).clip(80, 16000);
e = SinOsc.ar(d * (1 + (LFNoise1.kr(0.3).range(-0.02, 0.02) * drf)));

f = (c * e) * (2 + (mod * 3));   // ring mod
g = (f * (1 + (grt * 6))).tanh;

// Under-bed so drone mode is never silent
h = PinkNoise.ar(0.02) * (1 - (drp * 0.9));
i = HPF.ar(h, 120);

// Space tail
j = CombC.ar(g, 0.3, (0.01 + (spc * 0.16)).clip(0.01, 0.22), 0.4 + (spc * 1.4));
sig = (g * 0.9) + (j * 0.5) + (i * 0.3);

    // MANDATORY output chain (this order):
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_clockwork_refinery loaded".postln;
