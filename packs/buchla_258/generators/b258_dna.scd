// buchla_258/b258_dna — Full Dual-Waveform DNA Clone
/*
B258 DNA - Buchla 258 Forensic DNA Clone

FULL TABLE INTERPOLATION from 12-point 0-10V hardware telemetry.
Two independent oscillators with real SAW and SQR hardware captures.

=== HARDWARE ANALYSIS SUMMARY ===

SAW OUTPUT (top section):
  - Two-family piecewise with hard regime change at k≈0.77
  - h2 collapses to 0.12 then SNAPS back to 0.82
  - Character: "Hollow/vocal" → "Sawtooth saturated"

SQUARE OUTPUT (bottom section):
  - Single-family with softer transition at k≈0.55
  - h2 dips to 0.28 then recovers gradually
  - Starts purer (h3=0.01 vs saw's 0.05)
  - Character: "Pure pulse" → "Rich square"

=== CONTROL MAPPING ===

P0 SAW: Sine→Saw morph (independent, full hardware telemetry)
P1 SQR: Sine→Square morph (independent, full hardware telemetry)
P2 MIX: Blend between SAW and SQR oscillator signals

Data source: fingerprints/devices/buchla_258/
Multi-AI analysis: 2026-02-03 (Claude, ChatGPT, Gemini)
*/

SynthDef(\b258_dna, { |out, freqBus, customBus0|
    var sigSaw, sigSqr, sig, freq;
    var params, sawMorph, sqrMorph, mix;
    var sawK, sawKIdx, sawKFrac, sawI0, sawI1;
    var sqrK, sqrKIdx, sqrKFrac, sqrI0, sqrI1;
    var sawH1, sawH2, sawH3, sawH4, sawH5, sawH6, sawH7, sawH8;
    var sqrH1, sqrH2, sqrH3, sqrH4, sqrH5, sqrH6, sqrH7, sqrH8;
    var theta, rmsGainSaw, rmsGainSqr;

    // =======================================================
    // SAW HARMONIC TABLES (from 0-10V hardware telemetry)
    // =======================================================
    var h2SawT = #[0.5237, 0.5259, 0.5332, 0.5418, 0.5443, 0.5378, 0.5129, 0.3741, 0.1219, 0.8182, 0.8857, 0.8966];
    var h3SawT = #[0.0482, 0.0523, 0.0679, 0.0954, 0.1432, 0.2058, 0.2962, 0.4977, 0.6848, 0.5891, 0.5507, 0.5411];
    var h4SawT = #[0.0165, 0.0190, 0.0343, 0.0625, 0.1055, 0.1516, 0.2009, 0.2938, 0.4041, 0.4403, 0.4161, 0.4015];
    var h5SawT = #[0.0152, 0.0182, 0.0293, 0.0455, 0.0640, 0.0821, 0.0990, 0.1589, 0.2608, 0.3166, 0.3172, 0.3115];
    var h6SawT = #[0.0062, 0.0089, 0.0212, 0.0366, 0.0484, 0.0590, 0.0763, 0.1493, 0.2559, 0.2770, 0.2569, 0.2493];
    var h7SawT = #[0.0033, 0.0062, 0.0143, 0.0221, 0.0287, 0.0424, 0.0711, 0.1341, 0.2017, 0.2306, 0.2184, 0.2113];
    var h8SawT = #[0.0009, 0.0040, 0.0115, 0.0181, 0.0250, 0.0430, 0.0674, 0.1111, 0.1730, 0.1958, 0.1862, 0.1819];

    // =======================================================
    // SQUARE HARMONIC TABLES (from 0-10V hardware telemetry)
    // =======================================================
    var h2SqrT = #[0.5067, 0.5073, 0.5070, 0.5071, 0.5238, 0.5854, 0.2764, 0.3234, 0.4617, 0.5555, 0.6093, 0.6286];
    var h3SqrT = #[0.0106, 0.0108, 0.0106, 0.0108, 0.0294, 0.1403, 0.1990, 0.2714, 0.3161, 0.3334, 0.3406, 0.3434];
    var h4SqrT = #[0.0025, 0.0026, 0.0025, 0.0030, 0.0084, 0.0128, 0.1536, 0.2308, 0.2556, 0.2659, 0.2737, 0.2774];
    var h5SqrT = #[0.0065, 0.0064, 0.0066, 0.0069, 0.0164, 0.0636, 0.0910, 0.1343, 0.1676, 0.1901, 0.2017, 0.2050];
    var h6SqrT = #[0.0019, 0.0019, 0.0020, 0.0021, 0.0040, 0.0086, 0.0749, 0.1259, 0.1586, 0.1712, 0.1755, 0.1769];
    var h7SqrT = #[0.0025, 0.0025, 0.0026, 0.0027, 0.0086, 0.0358, 0.0570, 0.1035, 0.1269, 0.1371, 0.1437, 0.1456];
    var h8SqrT = #[0.0004, 0.0004, 0.0004, 0.0005, 0.0006, 0.0107, 0.0559, 0.0949, 0.1137, 0.1242, 0.1290, 0.1297];

    // =======================================================
    // INPUTS
    // =======================================================
    params = In.kr(customBus0, 3);
    sawMorph = Lag.kr(params[0], 0.05);  // P0 SAW
    sqrMorph = Lag.kr(params[1], 0.05);  // P1 SQR
    mix      = Lag.kr(params[2], 0.05);  // P2 MIX

    freq = In.kr(freqBus).clip(5, 20000);

    // =======================================================
    // SAW OSCILLATOR - Full Table Interpolation
    // =======================================================
    sawK = sawMorph.clip(0, 1);
    sawKIdx = sawK * 11;
    sawI0 = sawKIdx.floor.clip(0, 10);
    sawI1 = (sawI0 + 1).clip(0, 11);
    sawKFrac = sawKIdx - sawI0;

    sawH1 = 1.0;
    sawH2 = Select.kr(sawI0, h2SawT) + (sawKFrac * (Select.kr(sawI1, h2SawT) - Select.kr(sawI0, h2SawT)));
    sawH3 = Select.kr(sawI0, h3SawT) + (sawKFrac * (Select.kr(sawI1, h3SawT) - Select.kr(sawI0, h3SawT)));
    sawH4 = Select.kr(sawI0, h4SawT) + (sawKFrac * (Select.kr(sawI1, h4SawT) - Select.kr(sawI0, h4SawT)));
    sawH5 = Select.kr(sawI0, h5SawT) + (sawKFrac * (Select.kr(sawI1, h5SawT) - Select.kr(sawI0, h5SawT)));
    sawH6 = Select.kr(sawI0, h6SawT) + (sawKFrac * (Select.kr(sawI1, h6SawT) - Select.kr(sawI0, h6SawT)));
    sawH7 = Select.kr(sawI0, h7SawT) + (sawKFrac * (Select.kr(sawI1, h7SawT) - Select.kr(sawI0, h7SawT)));
    sawH8 = Select.kr(sawI0, h8SawT) + (sawKFrac * (Select.kr(sawI1, h8SawT) - Select.kr(sawI0, h8SawT)));

    // =======================================================
    // SQR OSCILLATOR - Full Table Interpolation
    // =======================================================
    sqrK = sqrMorph.clip(0, 1);
    sqrKIdx = sqrK * 11;
    sqrI0 = sqrKIdx.floor.clip(0, 10);
    sqrI1 = (sqrI0 + 1).clip(0, 11);
    sqrKFrac = sqrKIdx - sqrI0;

    sqrH1 = 1.0;
    sqrH2 = Select.kr(sqrI0, h2SqrT) + (sqrKFrac * (Select.kr(sqrI1, h2SqrT) - Select.kr(sqrI0, h2SqrT)));
    sqrH3 = Select.kr(sqrI0, h3SqrT) + (sqrKFrac * (Select.kr(sqrI1, h3SqrT) - Select.kr(sqrI0, h3SqrT)));
    sqrH4 = Select.kr(sqrI0, h4SqrT) + (sqrKFrac * (Select.kr(sqrI1, h4SqrT) - Select.kr(sqrI0, h4SqrT)));
    sqrH5 = Select.kr(sqrI0, h5SqrT) + (sqrKFrac * (Select.kr(sqrI1, h5SqrT) - Select.kr(sqrI0, h5SqrT)));
    sqrH6 = Select.kr(sqrI0, h6SqrT) + (sqrKFrac * (Select.kr(sqrI1, h6SqrT) - Select.kr(sqrI0, h6SqrT)));
    sqrH7 = Select.kr(sqrI0, h7SqrT) + (sqrKFrac * (Select.kr(sqrI1, h7SqrT) - Select.kr(sqrI0, h7SqrT)));
    sqrH8 = Select.kr(sqrI0, h8SqrT) + (sqrKFrac * (Select.kr(sqrI1, h8SqrT) - Select.kr(sqrI0, h8SqrT)));

    // =======================================================
    // ADDITIVE SYNTHESIS - Phase-aligned partials
    // =======================================================
    theta = Phasor.ar(0, freq / SampleRate.ir, 0, 2pi);

    // SAW oscillator
    sigSaw = (sawH1 * SinOsc.ar(0, theta))
           + (sawH2 * SinOsc.ar(0, theta * 2))
           + (sawH3 * SinOsc.ar(0, theta * 3))
           + (sawH4 * SinOsc.ar(0, theta * 4))
           + (sawH5 * SinOsc.ar(0, theta * 5))
           + (sawH6 * SinOsc.ar(0, theta * 6))
           + (sawH7 * SinOsc.ar(0, theta * 7))
           + (sawH8 * SinOsc.ar(0, theta * 8));

    // SQR oscillator
    sigSqr = (sqrH1 * SinOsc.ar(0, theta))
           + (sqrH2 * SinOsc.ar(0, theta * 2))
           + (sqrH3 * SinOsc.ar(0, theta * 3))
           + (sqrH4 * SinOsc.ar(0, theta * 4))
           + (sqrH5 * SinOsc.ar(0, theta * 5))
           + (sqrH6 * SinOsc.ar(0, theta * 6))
           + (sqrH7 * SinOsc.ar(0, theta * 7))
           + (sqrH8 * SinOsc.ar(0, theta * 8));

    // =======================================================
    // NORMALIZATION - RMS-based gain compensation per oscillator
    // =======================================================
    rmsGainSaw = (sawH1.squared + sawH2.squared + sawH3.squared + sawH4.squared +
                  sawH5.squared + sawH6.squared + sawH7.squared + sawH8.squared).sqrt.max(0.001).reciprocal;
    sigSaw = sigSaw * rmsGainSaw * 0.7;

    rmsGainSqr = (sqrH1.squared + sqrH2.squared + sqrH3.squared + sqrH4.squared +
                  sqrH5.squared + sqrH6.squared + sqrH7.squared + sqrH8.squared).sqrt.max(0.001).reciprocal;
    sigSqr = sigSqr * rmsGainSqr * 0.7;

    // =======================================================
    // MIX - Crossfade between SAW and SQR oscillators
    // =======================================================
    sig = (sigSaw * (1 - mix)) + (sigSqr * mix);

    // --- MANDATORY TAIL ---
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] b258_dna loaded (dual-waveform DNA clone from hardware telemetry)".postln;
