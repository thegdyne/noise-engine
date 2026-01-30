// clockwork_refinery/belt_rattle — Lightweight end-stage generator
// clockwork_refinery/belt_rattle.scd
// Clockwork Refinery — belt_rattle
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 DRF: drift / instability
// P2 GRT: grit / saturation
// P3 SPC: space / chamber
// P4 DRP: dropout / missing teeth
// P5 MOD: mode / coarse↔fine morph

SynthDef(\forge_clockwork_refinery_belt_rattle, { |out, freqBus, customBus0|

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

a = WhiteNoise.ar(0.20);
b = (2 + (mod * 14)).clip(2, 20);
c = (b * (1 + (LFNoise0.kr(2).range(-0.15, 0.15) * drf))).clip(0.5, 40);
d = LFPulse.kr(c, 0, 0.1 + (mod * 0.5)).lag(0.002);
e = (d > drp).asInteger; // dropout as missing pulses
f = a * d * e;

g = BPF.ar(f, (freq * (1 + (drf * 0.15))).clip(60, 12000), 0.2 + (mod * 0.4)) * (4 + (mod * 2));
h = CombC.ar(g, 0.25, (0.008 + (mod * 0.04)).clip(0.008, 0.2), 0.4 + (spc * 1.8));

sig = ((g * 0.8) + (h * 0.8));
sig = (sig * (1 + (grt * 4))).tanh;

    // MANDATORY output chain (this order):
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_clockwork_refinery loaded".postln;
