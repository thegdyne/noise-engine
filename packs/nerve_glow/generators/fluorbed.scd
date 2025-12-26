// FLUORBED -- Fluorescence spectral bed
// Evolving additive harmonics -- the glowing essence of fluorescent dyes

SynthDef(\forge_nerve_glow_fluorbed, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                        filterTypeBus, envEnabledBus, envSourceBus=0,
                                        clockRateBus, clockTrigBus,
                                        midiTrigBus=0, slotIndex=0,
                                        customBus0, customBus1, customBus2, customBus3, customBus4,
                                        portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var emission, spectrum, diffuse, freeze, aurora;
    var partials, numPartials, partialAmps, partialFreqs, drift;

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
    emission = In.kr(customBus0).linlin(0, 1, 4, 16);      // Number of audible partials
    spectrum = In.kr(customBus1).linlin(0, 1, 0.0, 0.1);  // Frequency drift amount
    diffuse = In.kr(customBus2).linexp(0, 1, 0.001, 0.05); // Detune/chorus
    freeze = In.kr(customBus3).linexp(0, 1, 0.5, 20);     // Partial sustain
    aurora = In.kr(customBus4).linexp(0, 1, 0.02, 0.5);   // Movement rate

    // Additive synthesis with drifting partials
    numPartials = 16;

    partials = Mix.fill(numPartials, { |i|
        var partialNum = i + 1;
        var baseFreq = freq * partialNum;

        // Amplitude rolloff with emission control
        var partialAmp = (emission - i).clip(0, 1) * (0.8 ** i);

        // Slow frequency drift (aurora)
        var freqDrift = SinOsc.kr(aurora * (0.5 + (i * 0.1)), i * 0.5, spectrum * partialNum);

        // Diffuse detuning
        var detune = LFNoise1.kr(aurora * 0.3).range(1 - diffuse, 1 + diffuse);

        // The partial
        SinOsc.ar((baseFreq + freqDrift).clip(20, 16000) * detune) * partialAmp
    });

    sig = partials * 0.15;

    // Add subtle beating/freeze sustain effect
    sig = sig * (1 + (SinOsc.kr(freeze.reciprocal, 0, 0.1)));

    // Warm compression
    sig = (sig * 2).tanh * 0.5;

    // Very slow stereo drift
    sig = [
        sig * (1 + SinOsc.kr(aurora * 0.2, 0, 0.1)),
        sig * (1 + SinOsc.kr(aurora * 0.2, pi * 0.5, 0.1))
    ];

    // Add very subtle high shimmer
    sig = sig + (SinOsc.ar(freq * 8 * LFNoise1.kr(aurora).range(0.99, 1.01)) * 0.02 * (emission / 16));

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  * forge_nerve_glow_fluorbed loaded".postln;
