// buchla_258/b258_dna — Full Table Interpolation DNA Clone
/*
B258 DNA - Buchla 258 Forensic DNA Clone

FULL TABLE INTERPOLATION from 12-point 0-10V hardware telemetry.
This generator recreates the EXACT harmonic behavior measured from real hardware,
including the non-monotonic h2 behavior and two-family regime change.

=== KEY FINDINGS FROM HARDWARE ANALYSIS ===

TWO-FAMILY PIECEWISE MODEL:

Family F1 (k = 0.00-0.73):
  - h2: 0.52 → 0.12 (COLLAPSE - asymmetry cancellation)
  - h3: 0.05 → 0.68 (PEAK - odd-dominant)
  - even/odd ratio: 8.0 → 0.8 (becomes odd-dominated)
  - Character: "Hollow/vocal" - the wavefolder nulling even harmonics

Family F2 (k = 0.82-1.00):
  - h2: 0.82 → 0.90 (SNAP BACK - new asymmetry mechanism)
  - h3: 0.59 → 0.54 (settles down)
  - even/odd ratio: ~1.5-1.6 (balanced)
  - Character: "Sawtooth-like" - saturated asymmetric

BREAKPOINT: k ≈ 0.77 (hard transition, not gradual)

=== CONTROL MAPPING ===

P1 MORPH: Main timbre control (maps to full 0-10V CV range)
P2 H2: Second harmonic scale (the 258's "soul")
P3 ODD: Odd harmonic scale (h3, h5, h7)
P4 EVEN: Even harmonic scale (h4, h6, h8)
P5 BRT: Brightness (h5-h8 boost)

Data source: fingerprints/devices/buchla_258/
Multi-AI analysis: 2026-02-03 (Claude, ChatGPT, Gemini consensus)
*/

SynthDef(\b258_dna, { |out, freqBus, customBus0|
    var sig, freq;
    var params, morph, h2Scale, oddScale, evenScale, brightness;
    var k, kIdx, kFrac, i0, i1;
    var h1, h2, h3, h4, h5, h6, h7, h8;
    var h2Raw, h3Raw, h4Raw, h5Raw, h6Raw, h7Raw, h8Raw;
    var theta, rmsGain;

    // =======================================================
    // HARDWARE TELEMETRY TABLES (12 points, 0-10V range)
    // From validated fingerprint extraction 2026-02-03
    // =======================================================

    // k values (normalized 0-1)
    var kTable  = #[0.000, 0.091, 0.182, 0.273, 0.364, 0.455, 0.545, 0.636, 0.727, 0.818, 0.909, 1.000];

    // Harmonic ratio tables (h1 = 1.0 always, not stored)
    var h2Table = #[0.5237, 0.5259, 0.5332, 0.5418, 0.5443, 0.5378, 0.5129, 0.3741, 0.1219, 0.8182, 0.8857, 0.8966];
    var h3Table = #[0.0482, 0.0523, 0.0679, 0.0954, 0.1432, 0.2058, 0.2962, 0.4977, 0.6848, 0.5891, 0.5507, 0.5411];
    var h4Table = #[0.0165, 0.0190, 0.0343, 0.0625, 0.1055, 0.1516, 0.2009, 0.2938, 0.4041, 0.4403, 0.4161, 0.4015];
    var h5Table = #[0.0152, 0.0182, 0.0293, 0.0455, 0.0640, 0.0821, 0.0990, 0.1589, 0.2608, 0.3166, 0.3172, 0.3115];
    var h6Table = #[0.0062, 0.0089, 0.0212, 0.0366, 0.0484, 0.0590, 0.0763, 0.1493, 0.2559, 0.2770, 0.2569, 0.2493];
    var h7Table = #[0.0033, 0.0062, 0.0143, 0.0221, 0.0287, 0.0424, 0.0711, 0.1341, 0.2017, 0.2306, 0.2184, 0.2113];
    var h8Table = #[0.0009, 0.0040, 0.0115, 0.0181, 0.0250, 0.0430, 0.0674, 0.1111, 0.1730, 0.1958, 0.1862, 0.1819];

    // =======================================================
    // INPUTS
    // =======================================================
    params = In.kr(customBus0, 5);
    morph      = Lag.kr(params[0], 0.05);  // P1 MORPH
    h2Scale    = Lag.kr(params[1], 0.05);  // P2 H2 scale
    oddScale   = Lag.kr(params[2], 0.05);  // P3 ODD scale
    evenScale  = Lag.kr(params[3], 0.05);  // P4 EVEN scale
    brightness = Lag.kr(params[4], 0.05);  // P5 BRT

    freq = In.kr(freqBus).clip(5, 20000);

    // =======================================================
    // TABLE INTERPOLATION
    // Linear interpolation between 12 table points
    // =======================================================

    k = morph.clip(0, 1);

    // Calculate table index and fraction
    // k=0 -> idx=0, k=1 -> idx=10 (11 segments for 12 points)
    kIdx = k * 11;
    i0 = kIdx.floor.clip(0, 10);
    i1 = (i0 + 1).clip(0, 11);
    kFrac = kIdx - i0;

    // Interpolate each harmonic from tables
    // Using Select for array indexing at control rate
    h2Raw = Select.kr(i0, h2Table) + (kFrac * (Select.kr(i1, h2Table) - Select.kr(i0, h2Table)));
    h3Raw = Select.kr(i0, h3Table) + (kFrac * (Select.kr(i1, h3Table) - Select.kr(i0, h3Table)));
    h4Raw = Select.kr(i0, h4Table) + (kFrac * (Select.kr(i1, h4Table) - Select.kr(i0, h4Table)));
    h5Raw = Select.kr(i0, h5Table) + (kFrac * (Select.kr(i1, h5Table) - Select.kr(i0, h5Table)));
    h6Raw = Select.kr(i0, h6Table) + (kFrac * (Select.kr(i1, h6Table) - Select.kr(i0, h6Table)));
    h7Raw = Select.kr(i0, h7Table) + (kFrac * (Select.kr(i1, h7Table) - Select.kr(i0, h7Table)));
    h8Raw = Select.kr(i0, h8Table) + (kFrac * (Select.kr(i1, h8Table) - Select.kr(i0, h8Table)));

    // =======================================================
    // USER SCALING
    // =======================================================
    h1 = 1.0;
    h2 = h2Raw * h2Scale;
    h3 = h3Raw * oddScale;
    h4 = h4Raw * evenScale;
    h5 = h5Raw * oddScale * brightness;
    h6 = h6Raw * evenScale * brightness;
    h7 = h7Raw * oddScale * brightness;
    h8 = h8Raw * evenScale * brightness;

    // =======================================================
    // ADDITIVE SYNTHESIS
    // Phase-aligned partials for clean harmonic spectrum
    // =======================================================
    theta = Phasor.ar(0, freq / SampleRate.ir, 0, 2pi);

    sig = (h1 * SinOsc.ar(0, theta))
        + (h2 * SinOsc.ar(0, theta * 2))
        + (h3 * SinOsc.ar(0, theta * 3))
        + (h4 * SinOsc.ar(0, theta * 4))
        + (h5 * SinOsc.ar(0, theta * 5))
        + (h6 * SinOsc.ar(0, theta * 6))
        + (h7 * SinOsc.ar(0, theta * 7))
        + (h8 * SinOsc.ar(0, theta * 8));

    // =======================================================
    // NORMALIZATION
    // RMS-based gain compensation for consistent output level
    // =======================================================
    rmsGain = (h1.squared + h2.squared + h3.squared + h4.squared +
               h5.squared + h6.squared + h7.squared + h8.squared).sqrt.max(0.001).reciprocal;
    sig = sig * rmsGain * 0.7;

    // --- MANDATORY TAIL ---
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] b258_dna loaded (full table interpolation from hardware telemetry)".postln;
