// core/b258_master — Lightweight end-stage generator
/*
B258 Master Generator
Digital reconstruction of Buchla 258 / Kassutronics Wavefolder behavior

Features:
  - Dual-branch topology: 7-stage folded sine core + band-limited sawtooth
  - Reciprocal control law for perceptual morphing
  - Geometric skew for odd/even harmonic tilt
  - Stabilized drive stage with per-stage tanh rounding

Custom params:
  - P1 shape: Morph from folded sine to sawtooth
  - P2 fold: 7-stage folding tension (harmonic bloom)
  - P3 glide: Frequency portamento weight
  - P4 symmetry: Odd/even harmonic bias
  - P5 saturation: Final hyperbolic drive
*/

SynthDef(\forge_core_b258_master, { |out, freqBus, customBus0|
    var sig, freq, p;
    var glide, shape, fold, sym, drive;
    var sine, saw, foldSig, foldAmt;
    var stages = 7;

    // Contiguous 5-channel custom bus read
    p = In.kr(customBus0, 5);

    // --- PARAMETER MAPPING (Elastic Smoothing) ---
    shape = Lag.kr(p[0], 0.08);
    fold  = Lag.kr(p[1], 0.06);
    glide = p[2].linexp(0, 1, 0.001, 0.5);
    sym   = Lag.kr(p[3].linlin(0, 1, -0.35, 0.35), 0.06);
    drive = p[4].linexp(0, 1, 1, 6);

    // Frequency with Inertia: Clamped to 5Hz - 20kHz range
    freq = Lag.kr(In.kr(freqBus).clip(5, 20000), glide);

    // --- BRANCH A: THE FOLDING CORE ---
    sine = SinOsc.ar(freq);

    // SYM: Fold-center offset + Geometric Skew (Odd/Even tilt)
    foldSig = sine + sym;
    foldSig = foldSig + (foldSig.squared * (sym * 0.4));

    // Strong Reciprocal Law: fold collapses as shape rises
    // Frequency-dependent scaling: taper fold at high pitches to prevent aliasing
    foldAmt = fold * (1 - shape).squared * freq.explin(1000, 8000, 1, 0.35);

    // Stabilized Drive Stage
    foldSig = foldSig * (1 + (foldAmt * 8));

    // 7-stage cascade with evolving thresholds
    stages.do { |i|
        var t = (0.9 - (i * 0.04)).clip(0.55, 0.95);
        var rec = 1.2 + (i * 0.02);
        foldSig = foldSig.fold2(t);
        foldSig = (foldSig * rec).tanh;
    };
    foldSig = foldSig * 0.9;
    // Post-fold anti-alias: frequency-tracking LPF catches residual foldover
    foldSig = LPF.ar(foldSig, (freq * 6).clip(200, 18000));
    foldSig = LeakDC.ar(foldSig);

    // --- BRANCH B: THE TARGET (De-aliased Sawtooth) ---
    saw = Saw.ar(freq);
    saw = LPF.ar(saw, (freq * (6 + (shape * 4))).clip(200, 18000));
    saw = (saw * 1.15).tanh;

    // --- TRANSITION PHASE (The Morph) ---
    sig = XFade2.ar(foldSig, saw, shape.linlin(0, 1, -1, 1));

    // Final Saturation & Headroom Management
    sig = (sig * drive).tanh;
    sig = sig * (1 - (0.12 * (shape * (1 - shape) * 4)));
    sig = LeakDC.ar(sig);

    // --- MANDATORY TAIL ---
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] forge_core_b258_master loaded".postln;
