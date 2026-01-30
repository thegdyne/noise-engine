// nerve_glow/nervespk — Lightweight end-stage generator
// NERVESPK -- Nerve impulse sparks
// Dust impulses through resonant filters, like neural firing patterns

SynthDef(\forge_nerve_glow_nervespk, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var density, axon, synapse, branch, gap;
    var impulses, resonators, sparkL, sparkR;

    // Standard bus reads
    freq = In.kr(freqBus);

    density = p[0].linlin(0, 1, 2, 40);  // Impulses per second
    axon = p[1].linexp(0, 1, 0.05, 2.0);  // Decay time
    synapse = p[2].linexp(0, 1, 0.5, 20);  // Resonance Q
    branch = p[3].linlin(0, 1, 1, 6);  // Number of harmonics
    gap = p[4].linlin(0, 1, 0.0, 0.5);  // Stereo width

    // Dual dust streams for stereo nerve branches
    impulses = Dust.ar(density);

    // Resonant filter bank at harmonic intervals (nerve branches)
    resonators = Mix.fill(6, { |i|
        var harmAmp = (branch - i).clip(0, 1);
        var harmFreq = freq * [1, 1.5, 2, 2.5, 3, 4].at(i);
        Ringz.ar(impulses, harmFreq.clip(20, 16000), axon, synapse.reciprocal) * harmAmp * 0.15
    });

    // Create stereo nerve spread
    sparkL = resonators;
    sparkR = DelayN.ar(resonators, 0.02, gap * 0.02);

    sig = [sparkL, sparkR];

    // Soft saturation for warmth
    sig = (sig * 2).tanh * 0.5;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  * forge_nerve_glow_nervespk loaded".postln;
