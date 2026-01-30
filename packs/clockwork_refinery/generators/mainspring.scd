// clockwork_refinery/mainspring — Lightweight end-stage generator
// clockwork_refinery/mainspring.scd
// Clockwork Refinery — mainspring
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 DRF: drift / instability
// P2 GRT: grit / saturation
// P3 SPC: space / chamber
// P4 DRP: dropout / missing teeth
// P5 MOD: mode / coarse↔fine morph

SynthDef(\forge_clockwork_refinery_mainspring, { |out, freqBus, customBus0|

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

a = (0.15 + (drf * 0.35)).clip(0.15, 0.6);
b = (0.2 + (mod * 0.75)).clip(0.2, 0.95); // pulse width-ish
c = Pulse.ar(freq * (1 + (LFNoise1.kr(a).range(-0.01, 0.01) * drf)), b) * 0.35;
d = SinOsc.ar(freq * 0.5) * 0.12;
e = c + d;

// "Spring tension" sweep into a narrow band
f = (freq * (1.5 + (mod * 6))).clip(80, 14000);
g = RLPF.ar(e, f, (0.12 + (mod * 0.5)).clip(0.12, 0.9)) * (1.5 + (mod * 1.5));

// Dropout + grit
h = g * (1 - (drp * 0.75));
i = (h * (1 + (grt * 6))).tanh;

// Space
j = CombC.ar(i, 0.25, (0.01 + (spc * 0.16)).clip(0.01, 0.22), 0.7 + (spc * 2.0));
sig = (i * 0.85) + (j * 0.4);

    // MANDATORY output chain (this order):
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_clockwork_refinery loaded".postln;
