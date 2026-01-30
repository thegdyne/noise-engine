// nerve_glow/striate — Lightweight end-stage generator
// STRIATE -- Muscle striations
// Rhythmic banded patterns -- the repeating structure of muscle tissue

SynthDef(\forge_nerve_glow_striate, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var band, rhythm, sweep, tension, gap;
    var noise, bands, bandFreq, gatePattern, sweepMod;

    // Standard bus reads
    freq = In.kr(freqBus);

    band = p[0].linexp(0, 1, 0.02, 0.3);  // Band Q (width)
    rhythm = p[1].linexp(0, 1, 2, 20);  // Pattern rate
    sweep = p[2].linlin(0, 1, 0.0, 0.5);  // Freq modulation
    tension = p[3].linexp(0, 1, 0.5, 10);  // Resonance
    gap = p[4].linlin(0, 1, 0.1, 0.9);  // Duty cycle

    // Rhythmic gate pattern
    gatePattern = LFPulse.kr(rhythm, 0, gap);

    // Sweep modulation
    sweepMod = SinOsc.kr(rhythm * 0.25, 0, sweep, 1);

    // Noise source with banding
    noise = PinkNoise.ar(1) + (WhiteNoise.ar(0.3));

    // Multiple resonant bands at harmonic intervals
    bands = Mix.fill(6, { |i|
        var bFreq = freq * (i + 1) * sweepMod;
        var bAmp = (0.7 ** i);
        RLPF.ar(noise, bFreq.clip(20, 16000), band) * bAmp * tension.sqrt
    });

    sig = bands * 0.2;

    // Apply rhythmic gating
    sig = sig * Lag.kr(gatePattern, 0.005);

    // Add transient click at band start
    sig = sig + (Impulse.ar(rhythm) * WhiteNoise.ar(0.05) * (1 - gap));

    // Stereo variation
    sig = [
        sig * (1 + (SinOsc.kr(rhythm * 0.1, 0, 0.1))),
        sig * (1 + (SinOsc.kr(rhythm * 0.1, pi, 0.1)))
    ];

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  * forge_nerve_glow_striate loaded".postln;
