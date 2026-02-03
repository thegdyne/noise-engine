// buchla_258/b258_twin — Buchla 258 Digital Twin
/*
B258 Twin - Buchla 258 Digital Twin

Based on empirical fingerprint analysis of real Buchla 258 hardware.
Uses additive synthesis with fitted harmonic coefficients.

Circuit insight (M.E.M.S. Project):
- Triangle core oscillator
- NOT a wavefolder - it's a crossfading mixer between shaped waveforms
- The "Timbre" CV morphs between sine-like and harmonically rich states

Fitted model (12-point hardware sweep, r > 0.89):
- Control curve: k^1.96 (convex - waits then surges)
- Harmonic growth: exponential decay with Gaussian bump at h3/h4
- Fixed h2 asymmetry: ~0.54 (baked into hardware shaping stage)

Custom params:
- P1 TIM: Timbre morph (0=sine-like, 1=rich harmonics)
- P2 BRT: Brightness (high harmonic emphasis)
- P3 ASY: Asymmetry (h2 amount - the 258 fingerprint)

Data source: fingerprints/devices/buchla_258/
Reference: https://www.memsproject.info/258-dual-sine-saw-oscillator
*/

SynthDef(\b258_twin, { |out,
    freqBus, cutoffBus, resBus, attackBus, decayBus,
    filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
    midiTrigBus=0, slotIndex=0,
    customBus0, customBus1, customBus2, customBus3, customBus4|

    // === BUS READS ===
    var freq = In.kr(freqBus);
    var filterFreq = In.kr(cutoffBus);
    var rq = In.kr(resBus);
    var attack = In.kr(attackBus);
    var decay = In.kr(decayBus);
    var filterType = In.kr(filterTypeBus);
    var envSource = In.kr(envSourceBus);
    var clockRate = In.kr(clockRateBus);

    // Custom parameters
    var timbre = In.kr(customBus0).clip(0, 1);      // Main morph control
    var brightness = In.kr(customBus1).clip(0, 1); // High harmonic emphasis
    var asymmetry = In.kr(customBus2).clip(0, 1);  // h2 amount (the 258 fingerprint)

    // === FITTED MODEL PARAMETERS ===
    // From hardware telemetry analysis (2026-02-03)
    var p = 1.96;           // Control curve exponent (convex)
    var capB = 0.177;       // Harmonic decay rate
    var mu = 3.54;          // Gaussian bump center
    var sigma = 0.64;       // Gaussian bump width
    var c0 = 0.17;          // Base sensitivity
    var c1 = 0.14;          // Bump sensitivity

    // Baseline harmonics at timbre=0 (measured from hardware)
    var h2Base = 0.523;
    var h3Base = 0.049;
    var h4Base = 0.018;
    var h5Base = 0.015;
    var h6Base = 0.006;
    var h7Base = 0.003;
    var h8Base = 0.001;

    // === DERIVED VALUES ===
    var k, brightnessScale, h2Scale;
    var h1, h2, h3, h4, h5, h6, h7, h8;
    var theta, sig, rmsGain;

    // Control curve: k^1.96 (the "wait then surge" behavior)
    k = timbre.pow(p);

    // Brightness scales the bump strength (user control for h5-h8)
    brightnessScale = brightness.linlin(0, 1, 0.5, 1.5);

    // Asymmetry scales h2 (the 258's "soul")
    h2Scale = asymmetry.linlin(0, 1, 0.0, 1.0);

    // === HARMONIC COEFFICIENT CALCULATION ===
    // h_n(k) = baseline + k * E(n) * F(n)
    // where E(n) = exp(-B*n), F(n) = c0 + c1*G(n), G(n) = gaussian bump

    // Calculate all harmonic amplitudes
    h1 = 1.0;
    h2 = h2Base * h2Scale;  // Fixed asymmetry, scaled by user

    // h3: n=3
    h3 = h3Base + (k * exp(-1 * capB * 3) * (c0 + (c1 * exp(-0.5 * ((3 - mu) / sigma).squared) * brightnessScale)));
    // h4: n=4
    h4 = h4Base + (k * exp(-1 * capB * 4) * (c0 + (c1 * exp(-0.5 * ((4 - mu) / sigma).squared) * brightnessScale)));
    // h5: n=5
    h5 = h5Base + (k * exp(-1 * capB * 5) * (c0 + (c1 * exp(-0.5 * ((5 - mu) / sigma).squared) * brightnessScale)));
    // h6: n=6
    h6 = h6Base + (k * exp(-1 * capB * 6) * (c0 + (c1 * exp(-0.5 * ((6 - mu) / sigma).squared) * brightnessScale)));
    // h7: n=7
    h7 = h7Base + (k * exp(-1 * capB * 7) * (c0 + (c1 * exp(-0.5 * ((7 - mu) / sigma).squared) * brightnessScale)));
    // h8: n=8
    h8 = h8Base + (k * exp(-1 * capB * 8) * (c0 + (c1 * exp(-0.5 * ((8 - mu) / sigma).squared) * brightnessScale)));

    // === ADDITIVE SYNTHESIS ===
    // Phase-aligned partials for clean harmonic spectrum
    theta = Phasor.ar(0, freq / SampleRate.ir, 0, 2pi);

    sig = (h1 * SinOsc.ar(0, theta))
        + (h2 * SinOsc.ar(0, theta * 2))
        + (h3 * SinOsc.ar(0, theta * 3))
        + (h4 * SinOsc.ar(0, theta * 4))
        + (h5 * SinOsc.ar(0, theta * 5))
        + (h6 * SinOsc.ar(0, theta * 6))
        + (h7 * SinOsc.ar(0, theta * 7))
        + (h8 * SinOsc.ar(0, theta * 8));

    // === NORMALIZATION ===
    // RMS-based gain compensation
    rmsGain = (h1.squared + h2.squared + h3.squared + h4.squared +
               h5.squared + h6.squared + h7.squared + h8.squared).sqrt.max(0.001).reciprocal;
    sig = sig * rmsGain * 0.7;  // 0.7 for headroom

    // === STANDARD POST-CHAIN (SSOT) ===
    sig = ~ensure2ch.(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, 1.0, clockTrigBus, midiTrigBus, slotIndex);

    Out.ar(out, sig);
}).add;

"  [x] b258_twin loaded".postln;
