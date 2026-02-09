// buchla_258/b258_dna26 — Lightweight end-stage generator
/*
B258 DNA26 - Buchla 258 Forensic DNA Clone (26-point)

FULL TABLE INTERPOLATION from 26-point 0-5V hardware telemetry.
Two independent oscillators with real SAW and SQR hardware captures.

Harmonic tables extracted via SSOT FFT (fft_features.compute_all)
from 1024-sample waveform captures in morph mapper sweeps (6 Feb 2026).
Each table entry is the harmonic magnitude normalized to the fundamental (h1=1.0).

Upgrade from b258_dna (12-point) to 26-point for higher morph resolution.

=== HARDWARE CAPTURE CONDITIONS ===

SAW sweep: 39.3 Hz, Sine->Saw, 26 points CC 0-125 (0-5.07V via CV.OCD)
  Source: morph_map_buchla_258_20260206_140115.json
SQR sweep: 49.8 Hz, Sine->Square, 26 points CC 0-125 (0-5.07V via CV.OCD)
  Source: morph_map_buchla_258_20260206_140441.json

=== CONTROL MAPPING ===

P0 SAW: Sine->Saw morph (independent, full hardware telemetry)
P1 SQR: Sine->Square morph (independent, full hardware telemetry)
P2 MIX: Blend between SAW and SQR oscillator signals

No filter/envelope — handled by channel strip end-stage.
*/

SynthDef(\b258_dna26, { |out, freqBus, customBus0|
    var sigSaw, sigSqr, sig, freq;
    var params, sawMorph, sqrMorph, mix;
    var sawK, sawKIdx, sawKFrac, sawI0, sawI1;
    var sqrK, sqrKIdx, sqrKFrac, sqrI0, sqrI1;
    var sawH1, sawH2, sawH3, sawH4, sawH5, sawH6, sawH7, sawH8;
    var sqrH1, sqrH2, sqrH3, sqrH4, sqrH5, sqrH6, sqrH7, sqrH8;
    var theta, rmsGainSaw, rmsGainSqr;
    var sawRmsComp, sqrRmsComp;

    // =======================================================
    // SAW HARMONIC TABLES (FFT from 1024-sample hardware waveforms)
    // 26 points: CC 0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100, 105, 110, 115, 120, 125
    // =======================================================
    var h2SawT = #[0.5263, 0.5268, 0.5292, 0.5313, 0.5338, 0.5372, 0.5407, 0.5420, 0.5434, 0.5420, 0.5382, 0.5315, 0.5219, 0.5045, 0.4807, 0.4297, 0.3257, 0.1362, 0.2036, 0.7783, 0.8111, 0.8735, 0.8932, 0.9028, 0.9056, 0.9068];
    var h3SawT = #[0.0513, 0.0530, 0.0562, 0.0615, 0.0687, 0.0799, 0.0933, 0.1101, 0.1311, 0.1552, 0.1836, 0.2185, 0.2560, 0.3020, 0.3633, 0.4422, 0.5507, 0.6717, 0.7253, 0.6432, 0.6204, 0.5785, 0.5631, 0.5570, 0.5491, 0.5492];
    var h4SawT = #[0.0180, 0.0189, 0.0212, 0.0261, 0.0331, 0.0457, 0.0598, 0.0769, 0.0953, 0.1157, 0.1384, 0.1624, 0.1856, 0.2134, 0.2424, 0.2800, 0.3288, 0.3837, 0.4455, 0.4614, 0.4602, 0.4346, 0.4207, 0.4132, 0.4024, 0.4018];
    var h5SawT = #[0.0153, 0.0165, 0.0187, 0.0222, 0.0282, 0.0351, 0.0437, 0.0532, 0.0622, 0.0724, 0.0824, 0.0911, 0.1002, 0.1123, 0.1249, 0.1512, 0.1914, 0.2471, 0.2898, 0.3305, 0.3304, 0.3265, 0.3249, 0.3249, 0.3214, 0.3213];
    var h6SawT = #[0.0060, 0.0068, 0.0093, 0.0134, 0.0193, 0.0272, 0.0347, 0.0425, 0.0488, 0.0551, 0.0605, 0.0655, 0.0722, 0.0842, 0.1019, 0.1289, 0.1721, 0.2286, 0.2805, 0.2913, 0.2902, 0.2732, 0.2657, 0.2626, 0.2583, 0.2582];
    var h7SawT = #[0.0035, 0.0045, 0.0065, 0.0093, 0.0137, 0.0185, 0.0228, 0.0271, 0.0303, 0.0341, 0.0390, 0.0464, 0.0576, 0.0739, 0.0942, 0.1225, 0.1588, 0.1985, 0.2273, 0.2435, 0.2417, 0.2340, 0.2295, 0.2266, 0.2224, 0.2222];
    var h8SawT = #[0.0010, 0.0019, 0.0041, 0.0070, 0.0108, 0.0150, 0.0179, 0.0215, 0.0242, 0.0290, 0.0360, 0.0460, 0.0574, 0.0716, 0.0862, 0.1060, 0.1324, 0.1631, 0.1954, 0.2089, 0.2067, 0.1993, 0.1963, 0.1949, 0.1922, 0.1920];

    // =======================================================
    // SQR HARMONIC TABLES (FFT from 1024-sample hardware waveforms)
    // 26 points: CC 0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100, 105, 110, 115, 120, 125
    // =======================================================
    var h2SqrT = #[0.5071, 0.5068, 0.5074, 0.5052, 0.5072, 0.5060, 0.5070, 0.5091, 0.5102, 0.5182, 0.5308, 0.5475, 0.5000, 0.3009, 0.2642, 0.2717, 0.3154, 0.3802, 0.4431, 0.4979, 0.5380, 0.5689, 0.5941, 0.6091, 0.6204, 0.6244];
    var h3SqrT = #[0.0115, 0.0117, 0.0120, 0.0105, 0.0115, 0.0111, 0.0118, 0.0143, 0.0170, 0.0287, 0.0557, 0.1095, 0.1794, 0.1829, 0.2071, 0.2366, 0.2682, 0.2939, 0.3122, 0.3218, 0.3311, 0.3338, 0.3390, 0.3383, 0.3368, 0.3402];
    var h4SqrT = #[0.0037, 0.0040, 0.0038, 0.0040, 0.0043, 0.0040, 0.0041, 0.0055, 0.0070, 0.0111, 0.0174, 0.0237, 0.0417, 0.1229, 0.1686, 0.2034, 0.2264, 0.2412, 0.2518, 0.2574, 0.2626, 0.2655, 0.2707, 0.2719, 0.2721, 0.2745];
    var h5SqrT = #[0.0065, 0.0065, 0.0066, 0.0065, 0.0065, 0.0066, 0.0067, 0.0064, 0.0095, 0.0156, 0.0283, 0.0494, 0.0704, 0.0776, 0.0976, 0.1157, 0.1326, 0.1483, 0.1641, 0.1761, 0.1867, 0.1929, 0.1987, 0.2011, 0.2012, 0.2035];
    var h6SqrT = #[0.0021, 0.0022, 0.0022, 0.0019, 0.0022, 0.0021, 0.0023, 0.0024, 0.0040, 0.0058, 0.0061, 0.0030, 0.0129, 0.0620, 0.0820, 0.1029, 0.1231, 0.1406, 0.1547, 0.1634, 0.1688, 0.1713, 0.1734, 0.1746, 0.1743, 0.1758];
    var h7SqrT = #[0.0026, 0.0025, 0.0026, 0.0027, 0.0025, 0.0026, 0.0027, 0.0036, 0.0043, 0.0078, 0.0145, 0.0261, 0.0391, 0.0455, 0.0645, 0.0841, 0.1018, 0.1148, 0.1246, 0.1305, 0.1353, 0.1385, 0.1414, 0.1435, 0.1437, 0.1452];
    var h8SqrT = #[0.0006, 0.0008, 0.0006, 0.0006, 0.0007, 0.0006, 0.0007, 0.0012, 0.0016, 0.0020, 0.0010, 0.0026, 0.0053, 0.0437, 0.0628, 0.0798, 0.0932, 0.1027, 0.1113, 0.1172, 0.1224, 0.1253, 0.1277, 0.1286, 0.1287, 0.1297];

    // =======================================================
    // RMS GAIN TABLES (normalized amplitude tracking across morph)
    // =======================================================
    var rmsSawT = #[0.7603, 0.7543, 0.7568, 0.7578, 0.7551, 0.7468, 0.7214, 0.7144, 0.6548, 0.6587, 0.6619, 0.6738, 0.6744, 0.6550, 0.6733, 0.6968, 0.7364, 0.6790, 0.7735, 0.6465, 0.6886, 0.7894, 0.9390, 0.8079, 0.9910, 1.0000];
    var rmsSqrT = #[0.6678, 0.6634, 0.6860, 0.7037, 0.6792, 0.7079, 0.6842, 0.6901, 0.6618, 0.6391, 0.6535, 0.6387, 0.6673, 0.7165, 0.6955, 0.7144, 0.8367, 0.7467, 0.7423, 0.8791, 0.8345, 0.7915, 0.9330, 0.8975, 0.8741, 1.0000];

    // =======================================================
    // INPUTS
    // =======================================================
    params = In.kr(customBus0, 5);
    sawMorph = Lag.kr(params[0], 0.05);
    sqrMorph = Lag.kr(params[1], 0.05);
    mix      = Lag.kr(params[2], 0.05);

    freq = In.kr(freqBus).clip(5, 20000);

    // =======================================================
    // SAW OSCILLATOR - Table Interpolation (26-point)
    // =======================================================
    sawK = sawMorph.clip(0, 1);
    sawKIdx = sawK * 25;
    sawI0 = sawKIdx.floor.clip(0, 24);
    sawI1 = (sawI0 + 1).clip(0, 25);
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
    // SQR OSCILLATOR - Table Interpolation (26-point)
    // =======================================================
    sqrK = sqrMorph.clip(0, 1);
    sqrKIdx = sqrK * 25;
    sqrI0 = sqrKIdx.floor.clip(0, 24);
    sqrI1 = (sqrI0 + 1).clip(0, 25);
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

"  [x] b258_dna26 loaded (26-point dual-waveform DNA clone from hardware telemetry)".postln;
