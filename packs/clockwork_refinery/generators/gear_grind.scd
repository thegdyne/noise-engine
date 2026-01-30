// clockwork_refinery/gear_grind — Lightweight end-stage generator
// clockwork_refinery/gear_grind.scd
// Clockwork Refinery — gear_grind
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 DRF: drift / instability
// P2 GRT: grit / saturation
// P3 SPC: space / chamber
// P4 DRP: dropout / missing teeth
// P5 MOD: mode / coarse↔fine morph

SynthDef(\forge_clockwork_refinery_gear_grind, { |out, freqBus, customBus0|

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

a = PinkNoise.ar(0.25) + BrownNoise.ar(0.10);
b = (0.3 + (drf * 2.2)).clip(0.3, 3.0);
c = LFNoise1.kr(b).exprange(120, 4200);
d = Resonz.ar(a, c, (0.05 + (mod * 0.25)).clip(0.05, 0.8)) * (3 + (mod * 4));

// Tooth-drop gating (continuous but with missing frames)
e = LFNoise0.kr(6 + (mod * 22)).range(0, 1);
f = (e > drp).asInteger;          // boolean safety
g = d * f;

// Grit + space
h = (g * (1 + (grt * 5))).tanh;
i = CombC.ar(h, 0.30, (0.02 + (spc * 0.18)).clip(0.02, 0.25), 0.8 + (spc * 2.4));
sig = (h * 0.85) + (i * 0.45);

    // MANDATORY output chain (this order):
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_clockwork_refinery loaded".postln;
