// buchla_258/b258_dna — Full Dual-Waveform DNA Clone
/*
B258 DNA - Buchla 258 Forensic DNA Clone

FULL TABLE INTERPOLATION from 12-point 0-5V hardware telemetry.
Two independent oscillators with real SAW and SQR hardware captures.

Harmonic tables extracted via FFT from 512-sample waveform captures
in buchla258_dual_comparison.html (4 Feb 2026). Each table entry is
the harmonic magnitude normalized to the fundamental (h1=1.0).

=== HARDWARE CAPTURE CONDITIONS ===

SAW sweep: 68.8 Hz, Sine→Saw, 12 points CC 0-125 (0-5.07V via CV.OCD)
SQR sweep: 50.3 Hz, Sine→Square, 12 points CC 0-125 (0-5.07V via CV.OCD)

=== SANITY CHECKS ===

SAW CC125: h2=0.41, h3=0.33, h4=0.24 — follows ~1/n saw series (0.82-0.99x ideal)
SQR CC125: odd h3=0.38, h5=0.23, h7=0.16 >> even h2=0.09, h4=0.05, h6=0.03
           Confirms genuine square-like waveform with strong odd harmonics.

=== CONTROL MAPPING ===

P0 SAW: Sine→Saw morph (independent, full hardware telemetry)
P1 SQR: Sine→Square morph (independent, full hardware telemetry)
P2 MIX: Blend between SAW and SQR oscillator signals

Data source: morph mapper sweep → buchla258_dual_comparison.html waveforms
*/

SynthDef(\b258_dna, { |out, freqBus, customBus0|
    var sigSaw, sigSqr, sig, freq;
    var params, sawMorph, sqrMorph, mix;
    var sawK, sawKIdx, sawKFrac, sawI0, sawI1;
    var sqrK, sqrKIdx, sqrKFrac, sqrI0, sqrI1;
    var sawH1, sawH2, sawH3, sawH4, sawH5, sawH6, sawH7, sawH8;
    var sqrH1, sqrH2, sqrH3, sqrH4, sqrH5, sqrH6, sqrH7, sqrH8;
    var theta, rmsGainSaw, rmsGainSqr;
    var sawRmsComp, sqrRmsComp;

    // =======================================================
    // SAW HARMONIC TABLES (FFT from 512-sample hardware waveforms)
    // 12 points: CC 0,11,23,34,46,57,68,80,91,102,114,125
    // =======================================================
    var h2SawT = #[0.0117, 0.0159, 0.0313, 0.0610, 0.1073, 0.1708, 0.2500, 0.3321, 0.3296, 0.2912, 0.3757, 0.4100];
    var h3SawT = #[0.0449, 0.0488, 0.0633, 0.0886, 0.1283, 0.1741, 0.2240, 0.3184, 0.4047, 0.4082, 0.3488, 0.3288];
    var h4SawT = #[0.0077, 0.0119, 0.0274, 0.0508, 0.0774, 0.1059, 0.1319, 0.1558, 0.1751, 0.2126, 0.2347, 0.2354];
    var h5SawT = #[0.0219, 0.0252, 0.0347, 0.0464, 0.0602, 0.0735, 0.0892, 0.1303, 0.1745, 0.1745, 0.1786, 0.1837];
    var h6SawT = #[0.0072, 0.0034, 0.0079, 0.0220, 0.0387, 0.0508, 0.0675, 0.1011, 0.1348, 0.1559, 0.1494, 0.1485];
    var h7SawT = #[0.0064, 0.0092, 0.0196, 0.0301, 0.0354, 0.0474, 0.0679, 0.0993, 0.1203, 0.1220, 0.1319, 0.1306];
    var h8SawT = #[0.0080, 0.0106, 0.0169, 0.0224, 0.0289, 0.0412, 0.0556, 0.0753, 0.0947, 0.1051, 0.1065, 0.1113];

    // =======================================================
    // SQUARE HARMONIC TABLES (FFT from 512-sample hardware waveforms)
    // =======================================================
    var h2SqrT = #[0.0094, 0.0083, 0.0087, 0.0094, 0.0261, 0.1362, 0.3954, 0.4050, 0.3109, 0.2158, 0.1280, 0.0928];
    var h3SqrT = #[0.0137, 0.0134, 0.0126, 0.0139, 0.0274, 0.1058, 0.3075, 0.4281, 0.4428, 0.4234, 0.3920, 0.3763];
    var h4SqrT = #[0.0009, 0.0010, 0.0009, 0.0019, 0.0106, 0.0404, 0.1222, 0.1472, 0.1303, 0.1025, 0.0643, 0.0462];
    var h5SqrT = #[0.0069, 0.0069, 0.0074, 0.0074, 0.0167, 0.0603, 0.1782, 0.2298, 0.2429, 0.2461, 0.2353, 0.2257];
    var h6SqrT = #[0.0025, 0.0024, 0.0026, 0.0027, 0.0051, 0.0209, 0.0891, 0.1026, 0.0798, 0.0603, 0.0404, 0.0313];
    var h7SqrT = #[0.0033, 0.0033, 0.0028, 0.0033, 0.0073, 0.0416, 0.1228, 0.1682, 0.1749, 0.1716, 0.1660, 0.1599];
    var h8SqrT = #[0.0009, 0.0010, 0.0010, 0.0008, 0.0013, 0.0177, 0.0652, 0.0751, 0.0622, 0.0459, 0.0298, 0.0247];

    // =======================================================
    // RMS GAIN TABLES (normalized amplitude tracking across morph)
    // =======================================================
    var rmsSawT = #[0.8988, 0.8953, 0.8816, 0.8596, 0.8322, 0.8041, 0.7791, 0.7680, 0.7924, 0.8466, 0.9323, 1.0000];
    var rmsSqrT = #[0.7480, 0.7483, 0.7479, 0.7463, 0.7278, 0.6518, 0.6626, 0.7355, 0.7838, 0.8454, 0.9345, 1.0000];

    // =======================================================
    // INPUTS
    // =======================================================
    params = In.kr(customBus0, 5);
    sawMorph = Lag.kr(params[0], 0.05);
    sqrMorph = Lag.kr(params[1], 0.05);
    mix      = Lag.kr(params[2], 0.05);

    freq = In.kr(freqBus).clip(5, 20000);

    // =======================================================
    // SAW OSCILLATOR - Table Interpolation
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

    sawRmsComp = Select.kr(sawI0, rmsSawT) + (sawKFrac * (Select.kr(sawI1, rmsSawT) - Select.kr(sawI0, rmsSawT)));

    // =======================================================
    // SQR OSCILLATOR - Table Interpolation
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

    sqrRmsComp = Select.kr(sqrI0, rmsSqrT) + (sqrKFrac * (Select.kr(sqrI1, rmsSqrT) - Select.kr(sqrI0, rmsSqrT)));

    // =======================================================
    // ADDITIVE SYNTHESIS - Phase-aligned partials
    // =======================================================
    theta = Phasor.ar(0, freq / SampleRate.ir, 0, 2pi);

    sigSaw = (sawH1 * SinOsc.ar(0, theta))
           + (sawH2 * SinOsc.ar(0, theta * 2))
           + (sawH3 * SinOsc.ar(0, theta * 3))
           + (sawH4 * SinOsc.ar(0, theta * 4))
           + (sawH5 * SinOsc.ar(0, theta * 5))
           + (sawH6 * SinOsc.ar(0, theta * 6))
           + (sawH7 * SinOsc.ar(0, theta * 7))
           + (sawH8 * SinOsc.ar(0, theta * 8));

    sigSqr = (sqrH1 * SinOsc.ar(0, theta))
           + (sqrH2 * SinOsc.ar(0, theta * 2))
           + (sqrH3 * SinOsc.ar(0, theta * 3))
           + (sqrH4 * SinOsc.ar(0, theta * 4))
           + (sqrH5 * SinOsc.ar(0, theta * 5))
           + (sqrH6 * SinOsc.ar(0, theta * 6))
           + (sqrH7 * SinOsc.ar(0, theta * 7))
           + (sqrH8 * SinOsc.ar(0, theta * 8));

    // =======================================================
    // NORMALIZATION
    // RMS-based gain compensation + hardware amplitude tracking
    // =======================================================
    rmsGainSaw = (sawH1.squared + sawH2.squared + sawH3.squared + sawH4.squared +
                  sawH5.squared + sawH6.squared + sawH7.squared + sawH8.squared).sqrt.max(0.001).reciprocal;
    sigSaw = sigSaw * rmsGainSaw * sawRmsComp * 0.7;

    rmsGainSqr = (sqrH1.squared + sqrH2.squared + sqrH3.squared + sqrH4.squared +
                  sqrH5.squared + sqrH6.squared + sqrH7.squared + sqrH8.squared).sqrt.max(0.001).reciprocal;
    sigSqr = sigSqr * rmsGainSqr * sqrRmsComp * 0.7;

    // =======================================================
    // MIX - Crossfade between SAW and SQR oscillators
    // =======================================================
    sig = (sigSaw * (1 - mix)) + (sigSqr * mix);

    // --- MANDATORY TAIL ---
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] b258_dna loaded (dual-waveform DNA clone from hardware telemetry)".postln;
