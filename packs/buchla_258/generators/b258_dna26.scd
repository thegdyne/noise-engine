// buchla_258/b258_dna26 — Lightweight end-stage generator
/*
B258 DNA26 - Buchla 258 Forensic DNA Clone (26-point)

FULL TABLE INTERPOLATION from 26-point 0-5V hardware telemetry.
Two independent oscillators with real SAW and SQR hardware captures.

Harmonic tables: h2-h8 ratios normalized to h1=1.0, extracted from
hw_dna.harmonic_signature in morph mapper sweeps (6 Feb 2026).
RMS tables: shape_rms from three-track decomposition, normalized to max=1.0.

=== HARDWARE CAPTURE CONDITIONS ===

SAW sweep: 39.3 Hz, Sine->Saw, 26 points CC 0-125 (0-5V via CV.OCD)
  Source: morph_map_buchla_258_20260206_140115.json
SQR sweep: 49.8 Hz, Sine->Square, 26 points CC 0-125 (0-5V via CV.OCD)
  Source: morph_map_buchla_258_20260206_140441.json
  Note: SQR CC0 data replaced with CC5 (anomalous capture at sweep start,
        crest=2.18 vs expected ~1.43 for sine)

=== TABLE DERIVATION ===

harmonic_signature from analysis gives [h1, h2, h3, ..., h8] where h1 >> 1.0.
Tables store h_n / h1 for n=2..8, so all values are relative to fundamental.
Additive synthesis with h1=1.0 then rmsGain normalizes total energy to unity.
rmsSawT/rmsSqrT restore the hardware's actual amplitude envelope.

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
    // SAW HARMONIC TABLES (26-point, h2-h8 normalized to h1=1.0)
    // Source: morph_map_buchla_258_20260206_140115.json
    // =======================================================
    var h2SawT = #[0.0538, 0.0532, 0.0518, 0.0545, 0.0563, 0.0573, 0.0620, 0.0659, 0.0764, 0.0790, 0.0906, 0.0920, 0.1043, 0.1126, 0.1097, 0.1195, 0.1233, 0.1255, 0.1363, 0.1418, 0.1358, 0.1396, 0.1290, 0.1351, 0.1341, 0.1319];
    var h3SawT = #[0.0538, 0.0532, 0.0518, 0.0495, 0.0469, 0.0485, 0.0455, 0.0465, 0.0473, 0.0481, 0.0583, 0.0552, 0.0638, 0.0714, 0.0574, 0.0634, 0.0708, 0.0638, 0.0762, 0.0824, 0.0752, 0.0803, 0.0687, 0.0731, 0.0732, 0.0675];
    var h4SawT = #[0.0538, 0.0532, 0.0518, 0.0495, 0.0469, 0.0441, 0.0413, 0.0426, 0.0400, 0.0412, 0.0453, 0.0399, 0.0493, 0.0522, 0.0392, 0.0415, 0.0457, 0.0383, 0.0541, 0.0632, 0.0514, 0.0576, 0.0469, 0.0477, 0.0457, 0.0435];
    var h5SawT = #[0.0538, 0.0532, 0.0518, 0.0495, 0.0469, 0.0441, 0.0413, 0.0388, 0.0400, 0.0378, 0.0388, 0.0337, 0.0435, 0.0467, 0.0287, 0.0317, 0.0342, 0.0277, 0.0421, 0.0498, 0.0367, 0.0471, 0.0302, 0.0350, 0.0335, 0.0300];
    var h6SawT = #[0.0538, 0.0532, 0.0518, 0.0495, 0.0469, 0.0441, 0.0413, 0.0388, 0.0400, 0.0344, 0.0421, 0.0307, 0.0435, 0.0412, 0.0287, 0.0268, 0.0251, 0.0213, 0.0301, 0.0460, 0.0367, 0.0436, 0.0201, 0.0286, 0.0244, 0.0210];
    var h7SawT = #[0.0538, 0.0532, 0.0518, 0.0495, 0.0469, 0.0441, 0.0413, 0.0388, 0.0400, 0.0344, 0.0356, 0.0307, 0.0377, 0.0330, 0.0287, 0.0268, 0.0228, 0.0234, 0.0220, 0.0441, 0.0294, 0.0349, 0.0168, 0.0286, 0.0168, 0.0150];
    var h8SawT = #[0.0538, 0.0532, 0.0518, 0.0495, 0.0469, 0.0441, 0.0413, 0.0388, 0.0400, 0.0344, 0.0356, 0.0307, 0.0319, 0.0302, 0.0261, 0.0268, 0.0228, 0.0213, 0.0220, 0.0498, 0.0349, 0.0244, 0.0168, 0.0318, 0.0152, 0.0165];

    // =======================================================
    // SQR HARMONIC TABLES (26-point, h2-h8 normalized to h1=1.0)
    // Source: morph_map_buchla_258_20260206_140441.json
    // Note: CC0 replaced with CC5 data (anomalous capture at sweep start)
    // =======================================================
    var h2SqrT = #[0.0500, 0.0500, 0.0503, 0.0503, 0.0553, 0.0503, 0.0503, 0.0500, 0.0498, 0.0531, 0.0543, 0.0698, 0.0873, 0.0991, 0.0974, 0.1083, 0.0940, 0.1121, 0.1006, 0.1103, 0.1076, 0.1075, 0.1268, 0.1195, 0.1191, 0.1184];
    var h3SqrT = #[0.0500, 0.0500, 0.0503, 0.0503, 0.0553, 0.0503, 0.0503, 0.0500, 0.0498, 0.0483, 0.0498, 0.0465, 0.0482, 0.0484, 0.0562, 0.0508, 0.0405, 0.0405, 0.0511, 0.0551, 0.0374, 0.0412, 0.0510, 0.0478, 0.0574, 0.0543];
    var h4SqrT = #[0.0500, 0.0500, 0.0503, 0.0503, 0.0503, 0.0503, 0.0503, 0.0500, 0.0498, 0.0483, 0.0498, 0.0426, 0.0331, 0.0346, 0.0543, 0.0406, 0.0389, 0.0202, 0.0619, 0.0551, 0.0344, 0.0353, 0.0394, 0.0281, 0.0588, 0.0474];
    var h5SqrT = #[0.0500, 0.0500, 0.0503, 0.0503, 0.0503, 0.0503, 0.0503, 0.0500, 0.0498, 0.0483, 0.0452, 0.0426, 0.0271, 0.0276, 0.0449, 0.0423, 0.0357, 0.0218, 0.0681, 0.0567, 0.0404, 0.0427, 0.0612, 0.0225, 0.0674, 0.0515];
    var h6SqrT = #[0.0500, 0.0500, 0.0503, 0.0503, 0.0503, 0.0503, 0.0503, 0.0500, 0.0498, 0.0483, 0.0452, 0.0388, 0.0241, 0.0184, 0.0243, 0.0406, 0.0308, 0.0312, 0.0619, 0.0521, 0.0344, 0.0368, 0.0496, 0.0295, 0.0631, 0.0404];
    var h7SqrT = #[0.0500, 0.0500, 0.0503, 0.0503, 0.0503, 0.0503, 0.0503, 0.0500, 0.0498, 0.0483, 0.0407, 0.0388, 0.0151, 0.0115, 0.0075, 0.0237, 0.0194, 0.0296, 0.0464, 0.0368, 0.0209, 0.0236, 0.0364, 0.0323, 0.0488, 0.0223];
    var h8SqrT = #[0.0500, 0.0500, 0.0503, 0.0503, 0.0503, 0.0503, 0.0503, 0.0500, 0.0498, 0.0483, 0.0407, 0.0388, 0.0151, 0.0069, 0.0112, 0.0237, 0.0097, 0.0140, 0.0248, 0.0230, 0.0090, 0.0088, 0.0408, 0.0211, 0.0273, 0.0181];

    // =======================================================
    // RMS GAIN TABLES (shape_rms from three-track decomposition, normalized to max=1.0)
    // Tracks the hardware's actual amplitude envelope across the morph range.
    // =======================================================
    var rmsSawT = #[0.8951, 0.8951, 0.8951, 0.8889, 0.8827, 0.8765, 0.8642, 0.8580, 0.8457, 0.8333, 0.8210, 0.8086, 0.7963, 0.7840, 0.7778, 0.7716, 0.7716, 0.7778, 0.7963, 0.8148, 0.8395, 0.8704, 0.9012, 0.9444, 0.9877, 1.0000];
    var rmsSqrT = #[0.7570, 0.7570, 0.7570, 0.7570, 0.7570, 0.7570, 0.7570, 0.7570, 0.7523, 0.7430, 0.7196, 0.6776, 0.6402, 0.6449, 0.6822, 0.7150, 0.7430, 0.7617, 0.7804, 0.8084, 0.8364, 0.8692, 0.9019, 0.9439, 0.9860, 1.0000];

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
    // rmsGain: normalize additive sum to unit RMS
    // rmsComp: restore hardware amplitude envelope across morph
    // 0.7: global output level scalar
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
