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

=== DUAL OSCILLATOR ARCHITECTURE ===

OSC A (SAW): Full telemetry tables - all harmonics (h2-h8)
  - True sine→saw morphing from hardware measurements
  - Includes the non-monotonic h2 behavior and regime change

OSC B (SQR): Odd harmonics only from telemetry (h3, h5, h7)
  - Even harmonics (h2, h4, h6, h8) zeroed for square character
  - Same table interpolation, same hardware truth

MIX: Crossfade between OSC A and OSC B signals

=== CONTROL MAPPING ===

P0 SAW: Sine→Saw morph (full hardware telemetry)
P1 SQR: Sine→Square morph (odd harmonics from telemetry)
P2 MIX: Blend between SAW and SQR oscillators

Data source: fingerprints/devices/buchla_258/
Multi-AI analysis: 2026-02-03 (Claude, ChatGPT, Gemini consensus)
*/

SynthDef(\b258_dna, { |out, freqBus, customBus0|
    var sigSaw, sigSqr, sig, freq;
    var params, sawMorph, sqrMorph, mix;
    var sawK, sawKIdx, sawKFrac, sawI0, sawI1;
    var sqrK, sqrKIdx, sqrKFrac, sqrI0, sqrI1;
    var sawH1, sawH2, sawH3, sawH4, sawH5, sawH6, sawH7, sawH8;
    var sqrH1, sqrH3, sqrH5, sqrH7;
    var theta, rmsGainSaw, rmsGainSqr;

    // =======================================================
    // HARDWARE TELEMETRY TABLES (12 points, 0-10V range)
    // From validated fingerprint extraction 2026-02-03
    // =======================================================

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
    params = In.kr(customBus0, 3);
    sawMorph = Lag.kr(params[0], 0.05);  // P0 SAW
    sqrMorph = Lag.kr(params[1], 0.05);  // P1 SQR
    mix      = Lag.kr(params[2], 0.05);  // P2 MIX

    freq = In.kr(freqBus).clip(5, 20000);

    // =======================================================
    // SAW OSCILLATOR - Full Table Interpolation (all harmonics)
    // =======================================================

    sawK = sawMorph.clip(0, 1);
    sawKIdx = sawK * 11;
    sawI0 = sawKIdx.floor.clip(0, 10);
    sawI1 = (sawI0 + 1).clip(0, 11);
    sawKFrac = sawKIdx - sawI0;

    // Interpolate all harmonics from tables
    sawH1 = 1.0;
    sawH2 = Select.kr(sawI0, h2Table) + (sawKFrac * (Select.kr(sawI1, h2Table) - Select.kr(sawI0, h2Table)));
    sawH3 = Select.kr(sawI0, h3Table) + (sawKFrac * (Select.kr(sawI1, h3Table) - Select.kr(sawI0, h3Table)));
    sawH4 = Select.kr(sawI0, h4Table) + (sawKFrac * (Select.kr(sawI1, h4Table) - Select.kr(sawI0, h4Table)));
    sawH5 = Select.kr(sawI0, h5Table) + (sawKFrac * (Select.kr(sawI1, h5Table) - Select.kr(sawI0, h5Table)));
    sawH6 = Select.kr(sawI0, h6Table) + (sawKFrac * (Select.kr(sawI1, h6Table) - Select.kr(sawI0, h6Table)));
    sawH7 = Select.kr(sawI0, h7Table) + (sawKFrac * (Select.kr(sawI1, h7Table) - Select.kr(sawI0, h7Table)));
    sawH8 = Select.kr(sawI0, h8Table) + (sawKFrac * (Select.kr(sawI1, h8Table) - Select.kr(sawI0, h8Table)));

    // =======================================================
    // SQR OSCILLATOR - Odd Harmonics Only from Tables
    // =======================================================

    sqrK = sqrMorph.clip(0, 1);
    sqrKIdx = sqrK * 11;
    sqrI0 = sqrKIdx.floor.clip(0, 10);
    sqrI1 = (sqrI0 + 1).clip(0, 11);
    sqrKFrac = sqrKIdx - sqrI0;

    // Interpolate ODD harmonics only (h3, h5, h7) - evens are zero
    sqrH1 = 1.0;
    sqrH3 = Select.kr(sqrI0, h3Table) + (sqrKFrac * (Select.kr(sqrI1, h3Table) - Select.kr(sqrI0, h3Table)));
    sqrH5 = Select.kr(sqrI0, h5Table) + (sqrKFrac * (Select.kr(sqrI1, h5Table) - Select.kr(sqrI0, h5Table)));
    sqrH7 = Select.kr(sqrI0, h7Table) + (sqrKFrac * (Select.kr(sqrI1, h7Table) - Select.kr(sqrI0, h7Table)));

    // =======================================================
    // ADDITIVE SYNTHESIS - Phase-aligned partials
    // =======================================================
    theta = Phasor.ar(0, freq / SampleRate.ir, 0, 2pi);

    // SAW oscillator: all harmonics
    sigSaw = (sawH1 * SinOsc.ar(0, theta))
           + (sawH2 * SinOsc.ar(0, theta * 2))
           + (sawH3 * SinOsc.ar(0, theta * 3))
           + (sawH4 * SinOsc.ar(0, theta * 4))
           + (sawH5 * SinOsc.ar(0, theta * 5))
           + (sawH6 * SinOsc.ar(0, theta * 6))
           + (sawH7 * SinOsc.ar(0, theta * 7))
           + (sawH8 * SinOsc.ar(0, theta * 8));

    // SQR oscillator: odd harmonics only
    sigSqr = (sqrH1 * SinOsc.ar(0, theta))
           + (sqrH3 * SinOsc.ar(0, theta * 3))
           + (sqrH5 * SinOsc.ar(0, theta * 5))
           + (sqrH7 * SinOsc.ar(0, theta * 7));

    // =======================================================
    // NORMALIZATION - RMS-based gain compensation per oscillator
    // =======================================================
    rmsGainSaw = (sawH1.squared + sawH2.squared + sawH3.squared + sawH4.squared +
                  sawH5.squared + sawH6.squared + sawH7.squared + sawH8.squared).sqrt.max(0.001).reciprocal;
    sigSaw = sigSaw * rmsGainSaw * 0.7;

    rmsGainSqr = (sqrH1.squared + sqrH3.squared + sqrH5.squared + sqrH7.squared).sqrt.max(0.001).reciprocal;
    sigSqr = sigSqr * rmsGainSqr * 0.7;

    // =======================================================
    // MIX - Crossfade between SAW and SQR oscillators
    // =======================================================
    sig = (sigSaw * (1 - mix)) + (sigSqr * mix);

    // --- MANDATORY TAIL ---
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] b258_dna loaded (full table interpolation from hardware telemetry)".postln;
