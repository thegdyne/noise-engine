// clockwork_refinery/intake_clunk — Lightweight end-stage generator
// clockwork_refinery/intake_clunk.scd
// Clockwork Refinery — intake_clunk
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 DRF: drift / instability
// P2 GRT: grit / saturation
// P3 SPC: space / chamber
// P4 DRP: dropout / missing teeth
// P5 MOD: mode / coarse↔fine morph

SynthDef(\forge_clockwork_refinery_intake_clunk, { |out, freqBus, customBus0|

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

// Internal hit source (hybrid initial + continuous)
a = (Impulse.ar(0) + Dust.ar(0.5 + (mod * 6))).clip2(1); // trigger
b = Decay2.ar(a, 0.001, 0.06 + (mod * 0.18));
c = WhiteNoise.ar(0.35) * b;

// Body modes (avoid .sum on non-array by making explicit array)
d = (freq * [0.75, 1.0, 1.33]).clip(30, 8000);
e = Ringz.ar(c, d * (1 + (LFNoise1.kr(0.15).range(-0.02, 0.02) * drf)), 0.12 + (mod * 0.25)).sum;

// Grit + dropout
f = e * (1 - (drp * 0.85));
g = (f * (1 + (grt * 6))).tanh;

// Space (duct bloom)
h = CombC.ar(g, 0.35, (0.015 + (spc * 0.22)).clip(0.015, 0.33), 1.2 + (spc * 2.0));
sig = (g * 0.7) + (h * 0.6) + (PinkNoise.ar(0.006) * (1 - drp));

    // MANDATORY output chain (this order):
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_clockwork_refinery loaded".postln;
