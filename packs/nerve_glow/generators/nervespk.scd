// NERVESPK -- Nerve impulse sparks
// Dust impulses through resonant filters, like neural firing patterns

SynthDef(\forge_nerve_glow_nervespk, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                        filterTypeBus, envEnabledBus, envSourceBus=0,
                                        clockRateBus, clockTrigBus,
                                        midiTrigBus=0, slotIndex=0,
                                        customBus0, customBus1, customBus2, customBus3, customBus4,
                                        portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var density, axon, synapse, branch, gap;
    var impulses, resonators, sparkL, sparkR;

    // Standard bus reads
    freq = In.kr(freqBus);
    portamento = In.kr(portamentoBus);
    freq = Lag.kr(freq, portamento.linexp(0, 1, 0.001, 0.5));
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);

    // Custom params
    density = In.kr(customBus0).linlin(0, 1, 2, 40);      // Impulses per second
    axon = In.kr(customBus1).linexp(0, 1, 0.05, 2.0);    // Decay time
    synapse = In.kr(customBus2).linexp(0, 1, 0.5, 20);   // Resonance Q
    branch = In.kr(customBus3).linlin(0, 1, 1, 6);       // Number of harmonics
    gap = In.kr(customBus4).linlin(0, 1, 0.0, 0.5);      // Stereo width

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

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  * forge_nerve_glow_nervespk loaded".postln;
