// buchla_258/b258_dna26 — Lightweight end-stage generator
/*
B258 DNA26 - Buchla 258 Forensic DNA Clone (26-point)

FULL TABLE INTERPOLATION from 26-point 0-5V hardware telemetry.
Two independent oscillators with real SAW and SQR hardware captures.

Harmonic tables extracted via rectangular-window FFT from 1024-sample
single-cycle waveform captures in morph mapper sweeps (6 Feb 2026).
Each table entry is the harmonic magnitude normalized to the fundamental (h1=1.0).

Rectangular window (no Hann) is required because the morph map waveforms
are single-cycle captures — Hann creates spurious h2 artefacts on
periodic-in-frame signals.

Upgrade from b258_dna (12-point) to 26-point for higher morph resolution.

=== HARDWARE CAPTURE CONDITIONS ===

SAW sweep: 39.3 Hz, Sine->Saw, 26 points CC 0-125 (0-5.07V via CV.OCD)
  Source: morph_map_buchla_258_20260206_140115.json
SQR sweep: 49.8 Hz, Sine->Square, 26 points CC 0-125 (0-5.07V via CV.OCD)
  Source: morph_map_buchla_258_20260206_140441.json

=== SANITY CHECKS ===

SAW CC125: h2=0.43, h3=0.35, h4=0.25 — follows ~1/n saw series (0.86-1.05x ideal)
SQR CC125: odd h3=0.38, h5=0.23, h7=0.16 >> even h2=0.10, h4=0.05, h6=0.03
           Confirms genuine square-like waveform with strong odd harmonics.

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
    // SAW HARMONIC TABLES (rectangular FFT, 1024-sample single-cycle waveforms)
    // 26 points: CC 0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100, 105, 110, 115, 120, 125
    // =======================================================
    var h2SawT = #[0.0075, 0.0096, 0.0113, 0.0181, 0.0246, 0.0350, 0.0458, 0.0663, 0.0875, 0.1107, 0.1371, 0.1686, 0.2008, 0.2333, 0.2741, 0.3137, 0.3479, 0.3722, 0.3490, 0.3117, 0.2961, 0.3215, 0.3678, 0.4008, 0.4249, 0.4286];
    var h3SawT = #[0.0509, 0.0534, 0.0548, 0.0607, 0.0675, 0.0761, 0.0860, 0.0996, 0.1162, 0.1304, 0.1492, 0.1695, 0.1907, 0.2131, 0.2424, 0.2784, 0.3230, 0.3776, 0.4165, 0.4384, 0.4415, 0.4193, 0.3889, 0.3689, 0.3511, 0.3492];
    var h4SawT = #[0.0012, 0.0024, 0.0057, 0.0098, 0.0163, 0.0261, 0.0386, 0.0487, 0.0606, 0.0750, 0.0891, 0.1024, 0.1171, 0.1315, 0.1432, 0.1553, 0.1663, 0.1718, 0.1845, 0.1964, 0.2157, 0.2379, 0.2501, 0.2537, 0.2516, 0.2497];
    var h5SawT = #[0.0160, 0.0168, 0.0195, 0.0224, 0.0277, 0.0338, 0.0424, 0.0482, 0.0551, 0.0628, 0.0698, 0.0763, 0.0830, 0.0910, 0.1001, 0.1159, 0.1385, 0.1658, 0.1789, 0.1929, 0.1921, 0.1843, 0.1844, 0.1907, 0.1945, 0.1961];
    var h6SawT = #[0.0016, 0.0025, 0.0045, 0.0080, 0.0129, 0.0191, 0.0249, 0.0311, 0.0372, 0.0410, 0.0462, 0.0518, 0.0563, 0.0646, 0.0745, 0.0868, 0.1014, 0.1185, 0.1396, 0.1511, 0.1630, 0.1697, 0.1665, 0.1630, 0.1596, 0.1585];
    var h7SawT = #[0.0031, 0.0041, 0.0055, 0.0082, 0.0121, 0.0163, 0.0201, 0.0245, 0.0284, 0.0321, 0.0372, 0.0432, 0.0508, 0.0614, 0.0727, 0.0880, 0.1036, 0.1212, 0.1268, 0.1296, 0.1295, 0.1302, 0.1358, 0.1388, 0.1392, 0.1397];
    var h8SawT = #[0.0009, 0.0010, 0.0032, 0.0058, 0.0094, 0.0135, 0.0168, 0.0206, 0.0234, 0.0285, 0.0341, 0.0407, 0.0485, 0.0570, 0.0644, 0.0727, 0.0822, 0.0900, 0.0992, 0.1064, 0.1108, 0.1153, 0.1164, 0.1181, 0.1181, 0.1176];

    // =======================================================
    // SQR HARMONIC TABLES (rectangular FFT, 1024-sample single-cycle waveforms)
    // 26 points: CC 0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100, 105, 110, 115, 120, 125
    // =======================================================
    var h2SqrT = #[0.0149, 0.0112, 0.0081, 0.0097, 0.0071, 0.0092, 0.0074, 0.0095, 0.0128, 0.0219, 0.0440, 0.0919, 0.1964, 0.3262, 0.4179, 0.4304, 0.4098, 0.3733, 0.3287, 0.2795, 0.2378, 0.1972, 0.1580, 0.1288, 0.1003, 0.0951];
    var h3SqrT = #[0.0129, 0.0126, 0.0116, 0.0121, 0.0108, 0.0117, 0.0115, 0.0126, 0.0153, 0.0225, 0.0416, 0.0799, 0.1421, 0.2358, 0.3397, 0.3991, 0.4267, 0.4417, 0.4452, 0.4407, 0.4305, 0.4174, 0.4056, 0.3910, 0.3802, 0.3782];
    var h4SqrT = #[0.0057, 0.0014, 0.0017, 0.0019, 0.0023, 0.0020, 0.0022, 0.0031, 0.0048, 0.0092, 0.0165, 0.0297, 0.0569, 0.0947, 0.1351, 0.1485, 0.1490, 0.1447, 0.1354, 0.1235, 0.1107, 0.0964, 0.0798, 0.0653, 0.0495, 0.0475];
    var h5SqrT = #[0.0113, 0.0063, 0.0072, 0.0067, 0.0075, 0.0072, 0.0074, 0.0078, 0.0097, 0.0146, 0.0239, 0.0431, 0.0852, 0.1443, 0.1933, 0.2185, 0.2293, 0.2366, 0.2423, 0.2462, 0.2473, 0.2456, 0.2419, 0.2352, 0.2285, 0.2270];
    var h6SqrT = #[0.0079, 0.0015, 0.0018, 0.0018, 0.0018, 0.0020, 0.0018, 0.0024, 0.0031, 0.0043, 0.0065, 0.0139, 0.0347, 0.0683, 0.0987, 0.1069, 0.1040, 0.0954, 0.0840, 0.0723, 0.0649, 0.0573, 0.0494, 0.0420, 0.0318, 0.0316];
    var h7SqrT = #[0.0061, 0.0023, 0.0022, 0.0026, 0.0019, 0.0021, 0.0022, 0.0023, 0.0031, 0.0059, 0.0126, 0.0292, 0.0586, 0.0974, 0.1351, 0.1566, 0.1674, 0.1730, 0.1749, 0.1745, 0.1730, 0.1713, 0.1693, 0.1660, 0.1622, 0.1610];
    var h8SqrT = #[0.0054, 0.0004, 0.0005, 0.0004, 0.0006, 0.0005, 0.0005, 0.0011, 0.0012, 0.0018, 0.0021, 0.0098, 0.0277, 0.0514, 0.0715, 0.0763, 0.0755, 0.0721, 0.0653, 0.0567, 0.0502, 0.0432, 0.0364, 0.0319, 0.0235, 0.0246];

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
