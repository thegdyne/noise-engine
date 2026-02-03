// buchla_258/b258_dna — Full Dual-Waveform DNA Clone
/*
B258 DNA - Buchla 258 Forensic DNA Clone

FULL TABLE INTERPOLATION from 12-point 0-10V hardware telemetry.
Includes BOTH saw and square outputs with crossfade.

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

P1 MORPH: Main timbre control (maps to 0-10V CV range)
P2 WAVE: SAW (0) to SQR (1) blend
P3 H2: Second harmonic scale
P4 HARM: Overall harmonic content (h3-h8)
P5 BRT: Brightness (h5-h8 boost)

Data source: fingerprints/devices/buchla_258_saw/ and buchla_258/
Multi-AI analysis: 2026-02-03 (Claude, ChatGPT, Gemini)
*/

SynthDef(\b258_dna, { |out, freqBus, customBus0|
    var sig, freq;
    var params, morph, waveMix, h2Scale, harmScale, brightness;
    var k, kIdx, kFrac, i0, i1;
    var h1, h2, h3, h4, h5, h6, h7, h8;
    var h2Saw, h3Saw, h4Saw, h5Saw, h6Saw, h7Saw, h8Saw;
    var h2Sqr, h3Sqr, h4Sqr, h5Sqr, h6Sqr, h7Sqr, h8Sqr;
    var theta, rmsGain;

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
    params = In.kr(customBus0, 5);
    morph      = Lag.kr(params[0], 0.05);  // P1 MORPH
    waveMix    = Lag.kr(params[1], 0.05);  // P2 WAVE (saw/sqr)
    h2Scale    = Lag.kr(params[2], 0.05);  // P3 H2 scale
    harmScale  = Lag.kr(params[3], 0.05);  // P4 HARM scale
    brightness = Lag.kr(params[4], 0.05);  // P5 BRT

    freq = In.kr(freqBus).clip(5, 20000);

    // =======================================================
    // TABLE INTERPOLATION
    // =======================================================
    k = morph.clip(0, 1);
    kIdx = k * 11;
    i0 = kIdx.floor.clip(0, 10);
    i1 = (i0 + 1).clip(0, 11);
    kFrac = kIdx - i0;

    // Interpolate SAW harmonics
    h2Saw = Select.kr(i0, h2SawT) + (kFrac * (Select.kr(i1, h2SawT) - Select.kr(i0, h2SawT)));
    h3Saw = Select.kr(i0, h3SawT) + (kFrac * (Select.kr(i1, h3SawT) - Select.kr(i0, h3SawT)));
    h4Saw = Select.kr(i0, h4SawT) + (kFrac * (Select.kr(i1, h4SawT) - Select.kr(i0, h4SawT)));
    h5Saw = Select.kr(i0, h5SawT) + (kFrac * (Select.kr(i1, h5SawT) - Select.kr(i0, h5SawT)));
    h6Saw = Select.kr(i0, h6SawT) + (kFrac * (Select.kr(i1, h6SawT) - Select.kr(i0, h6SawT)));
    h7Saw = Select.kr(i0, h7SawT) + (kFrac * (Select.kr(i1, h7SawT) - Select.kr(i0, h7SawT)));
    h8Saw = Select.kr(i0, h8SawT) + (kFrac * (Select.kr(i1, h8SawT) - Select.kr(i0, h8SawT)));

    // Interpolate SQUARE harmonics
    h2Sqr = Select.kr(i0, h2SqrT) + (kFrac * (Select.kr(i1, h2SqrT) - Select.kr(i0, h2SqrT)));
    h3Sqr = Select.kr(i0, h3SqrT) + (kFrac * (Select.kr(i1, h3SqrT) - Select.kr(i0, h3SqrT)));
    h4Sqr = Select.kr(i0, h4SqrT) + (kFrac * (Select.kr(i1, h4SqrT) - Select.kr(i0, h4SqrT)));
    h5Sqr = Select.kr(i0, h5SqrT) + (kFrac * (Select.kr(i1, h5SqrT) - Select.kr(i0, h5SqrT)));
    h6Sqr = Select.kr(i0, h6SqrT) + (kFrac * (Select.kr(i1, h6SqrT) - Select.kr(i0, h6SqrT)));
    h7Sqr = Select.kr(i0, h7SqrT) + (kFrac * (Select.kr(i1, h7SqrT) - Select.kr(i0, h7SqrT)));
    h8Sqr = Select.kr(i0, h8SqrT) + (kFrac * (Select.kr(i1, h8SqrT) - Select.kr(i0, h8SqrT)));

    // =======================================================
    // WAVEFORM BLEND (SAW <-> SQR)
    // =======================================================
    h1 = 1.0;
    h2 = ((h2Saw * (1 - waveMix)) + (h2Sqr * waveMix)) * h2Scale;
    h3 = ((h3Saw * (1 - waveMix)) + (h3Sqr * waveMix)) * harmScale;
    h4 = ((h4Saw * (1 - waveMix)) + (h4Sqr * waveMix)) * harmScale;
    h5 = ((h5Saw * (1 - waveMix)) + (h5Sqr * waveMix)) * harmScale * brightness;
    h6 = ((h6Saw * (1 - waveMix)) + (h6Sqr * waveMix)) * harmScale * brightness;
    h7 = ((h7Saw * (1 - waveMix)) + (h7Sqr * waveMix)) * harmScale * brightness;
    h8 = ((h8Saw * (1 - waveMix)) + (h8Sqr * waveMix)) * harmScale * brightness;

    // =======================================================
    // ADDITIVE SYNTHESIS
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
    // =======================================================
    rmsGain = (h1.squared + h2.squared + h3.squared + h4.squared +
               h5.squared + h6.squared + h7.squared + h8.squared).sqrt.max(0.001).reciprocal;
    sig = sig * rmsGain * 0.7;

    // --- MANDATORY TAIL ---
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] b258_dna loaded (dual-waveform DNA clone from hardware telemetry)".postln;
