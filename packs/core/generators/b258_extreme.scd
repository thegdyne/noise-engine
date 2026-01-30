// core/b258_extreme — Lightweight end-stage generator
/*
B258 Extreme Generator
Extreme high-harmonic variant of the B258 wavefolder.

Features:
  - 9-stage cascaded folding with softclip inter-stage rounding
  - Cubic + squared symmetry skew for complex odd/even tilt
  - Pre-fold DC hygiene for stability under extreme offset
  - Clamped pitch taper for spectral hygiene at high frequencies

Custom params:
  - P1 shape: Morph from 9-stage fold to saturated sawtooth
  - P2 fold: 9-stage folding tension (extreme bloom)
  - P3 glide: Frequency portamento weight
  - P4 symmetry: Cubic/squared harmonic bias
  - P5 saturation: Brutal hyperbolic drive (32x)
*/

SynthDef(\forge_core_b258_extreme, { |out, freqBus, customBus0|
    var sig, freq, p;
    var glide, shape, fold, sym, drive;
    var sine, saw, foldSig, foldAmt, taper;
    var stages = 9;

    // Contiguous 5-channel custom bus read
    p = In.kr(customBus0, 5);

    // --- PARAMETER MAPPING (Extreme Ranges) ---
    shape = Lag.kr(p[0], 0.08);
    fold  = Lag.kr(p[1], 0.06);
    glide = p[2].linexp(0, 1, 0.001, 0.5);
    // SYM: Extreme tilt with soft-limiting to prevent core-lock
    sym   = Lag.kr(p[3].linlin(0, 1, -1.5, 1.5), 0.06).tanh * 1.2;
    drive = p[4].linexp(0, 1, 1, 32);

    // Frequency with Inertia: Clamped to 5Hz - 20kHz range
    freq = Lag.kr(In.kr(freqBus).clip(5, 20000), glide);

    // --- BRANCH A: EXTREME FOLDING CORE ---
    sine = SinOsc.ar(freq);

    // SYM: Offset + Squared Skew + Cubed Skew for complex tilt
    foldSig = sine + sym;
    foldSig = foldSig + (foldSig.squared * (sym * 1.2));
    foldSig = foldSig + (foldSig.cubed * (sym.abs * 0.3));
    foldSig = LeakDC.ar(foldSig);

    // Clamped Pitch Taper: Prevents aliasing in extreme regimes
    taper = freq.clip(1000, 8000).linexp(1000, 8000, 1, 0.25);
    foldAmt = fold * (1 - shape).squared * taper;

    // Extreme Drive into folding range
    foldSig = foldSig * (1 + (foldAmt * 20));

    // 9-stage cascade (softclip preserves harmonic definition)
    stages.do { |i|
        var t = (0.95 - (i * 0.05)).clip(0.4, 0.95);
        var rec = 1.6 + (i * 0.08);
        foldSig = foldSig.fold2(t);
        foldSig = (foldSig * rec).softclip;
    };
    foldSig = foldSig * 0.85;
    // Post-fold anti-alias: frequency-tracking LPF catches residual foldover
    foldSig = LPF.ar(foldSig, (freq * 5).clip(150, 16000));
    foldSig = LeakDC.ar(foldSig);

    // --- BRANCH B: TARGET (Saturated Saw) ---
    saw = Saw.ar(freq);
    saw = LPF.ar(saw, (freq * (5 + (shape * 5))).clip(200, 18000));
    saw = (saw * 1.3).softclip;

    // --- TRANSITION PHASE (The Morph) ---
    sig = XFade2.ar(foldSig, saw, shape.linlin(0, 1, -1, 1));

    // Final Brutal Saturation & Mid-shape Headroom Trim
    sig = (sig * drive).tanh;
    sig = sig * (1 - (0.15 * (shape * (1 - shape) * 4)));
    sig = LeakDC.ar(sig);

    // --- MANDATORY TAIL ---
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] forge_core_b258_extreme loaded".postln;
