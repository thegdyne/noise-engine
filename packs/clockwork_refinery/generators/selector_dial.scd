// clockwork_refinery/selector_dial — Lightweight end-stage generator
// clockwork_refinery/selector_dial.scd
// Clockwork Refinery — selector_dial
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 DRF: drift / instability
// P2 GRT: grit / saturation
// P3 SPC: space / chamber
// P4 DRP: dropout / missing teeth
// P5 MOD: mode / coarse↔fine morph

SynthDef(\forge_clockwork_refinery_selector_dial, { |out, freqBus, customBus0|

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

// Dial steps (hybrid initial + occasional)
a = Impulse.kr(0) + Dust.kr(0.3 + (mod * 3));
b = Stepper.kr(a, 0, 0, 3, 1);  // 0..3
c = b / 3; // 0..1 for SelectX

d = SinOsc.ar(freq);
e = LFTri.ar(freq);
f = Saw.ar(freq);
g = Pulse.ar(freq, 0.5);

// Morph with a stepped center + drift wiggle
h = (c + (LFNoise1.kr(0.2).range(-0.12, 0.12) * drf)).clip(0, 1);
i = SelectX.ar(h * 3, [d, e, f, g]) * 0.35;

// Processing: dropout = missing cycles, grit = crush
j = (LFNoise0.kr(10 + (mod * 30)).range(0, 1) > drp).asInteger;
k = i * j;
l = (k * (1 + (grt * 8))).tanh;

// Space
m = CombC.ar(l, 0.3, (0.012 + (spc * 0.18)).clip(0.012, 0.25), 0.9 + (spc * 2.6));
sig = (l * 0.85) + (m * 0.45);

    // MANDATORY output chain (this order):
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_clockwork_refinery loaded".postln;
