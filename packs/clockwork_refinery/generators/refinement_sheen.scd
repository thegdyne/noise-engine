// clockwork_refinery/refinement_sheen — Lightweight end-stage generator
// clockwork_refinery/refinement_sheen.scd
// Clockwork Refinery — refinement_sheen
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 DRF: drift / instability
// P2 GRT: grit / saturation
// P3 SPC: space / chamber
// P4 DRP: dropout / missing teeth
// P5 MOD: mode / coarse↔fine morph

SynthDef(\forge_clockwork_refinery_refinement_sheen, { |out, freqBus, customBus0|

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

a = (1.0 + (mod * 5)).clip(1, 6);   // ratio-ish
b = (0.2 + (grt * 8)).clip(0.2, 8); // index-ish
c = LFNoise1.kr(0.08 + (drf * 0.4)).range(0.98, 1.02);

d = SinOsc.ar(freq * a * c) * b;
e = SinOsc.ar(freq, d) * 0.35;

// Dropout: spectral "holes" via AM mask
f = (LFNoise0.kr(4 + (mod * 24)).range(0, 1) > drp).asInteger;
g = e * f;

// Space sheen
h = AllpassC.ar(g, 0.25, (0.01 + (spc * 0.12)).clip(0.01, 0.18), 0.6 + (spc * 2.5));
sig = (g * 0.9) + (h * 0.5);

    // MANDATORY output chain (this order):
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_clockwork_refinery loaded".postln;
