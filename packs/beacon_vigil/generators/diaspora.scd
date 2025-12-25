// DIASPORA - Scattered granular voices
// Source: Dispersion, separation, scattered communities finding each other
// Role: Accent - burst texture of multiple scattered elements

SynthDef(\forge_beacon_vigil_diaspora, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                    filterTypeBus, envEnabledBus, envSourceBus=0,
                                    clockRateBus, clockTrigBus,
                                    midiTrigBus=0, slotIndex=0,
                                    customBus0, customBus1, customBus2, customBus3, customBus4,
                                    portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var sctr, voic, disp, root, memo;
    var grains, rootTone, memory, numVoices, scatter;

    // Custom params
    sctr = In.kr(customBus0);  // Scatter density
    voic = In.kr(customBus1);  // Voice count
    disp = In.kr(customBus2);  // Dispersion spread
    root = In.kr(customBus3);  // Root anchor
    memo = In.kr(customBus4);  // Memory trails

    // Standard reads
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

    // === DSP: Diaspora Scatter ===

    // Dust trigger for scatter
    scatter = Dust.kr(sctr.linexp(0, 1, 2, 40));

    // Multiple scattered grain voices
    grains = 8.collect({ |i|
        var voiceFreq, voiceAmp, grain, pan, active;

        // Voice activation based on voic param
        active = (voic * 8) >= (i + 1);

        // Dispersed frequency - each voice scattered from root
        voiceFreq = freq * (1 + (
            TRand.kr(-1, 1, scatter) * disp * 0.5 * (i + 1) / 8
        ));
        // Quantize some to harmonic ratios for musicality
        voiceFreq = Select.kr(i % 3, [
            voiceFreq,
            freq * [1, 1.5, 2, 2.5, 3, 4, 5, 6].at(i),
            voiceFreq
        ]);

        // Each grain: short burst envelope
        grain = SinOsc.ar(voiceFreq);
        grain = grain + (Pulse.ar(voiceFreq, 0.3) * 0.2);
        grain = grain * EnvGen.ar(
            Env.perc(0.001, TRand.kr(0.02, 0.15, scatter)),
            scatter
        );

        // Random pan position
        pan = TRand.kr(-1, 1, scatter);
        grain = Pan2.ar(grain, pan);

        // Scale by activation
        grain * active.asInteger * (1 / (i + 2).sqrt);
    });

    grains = Mix(grains) * 0.3;

    // Root tone: anchoring pitch that persists
    rootTone = SinOsc.ar(freq) * root * 0.4;
    rootTone = rootTone + (SinOsc.ar(freq * 0.5) * root * 0.2);
    rootTone = Pan2.ar(rootTone, 0);

    sig = grains + rootTone;

    // Memory: reverberant trails connecting to origin
    memory = sig;
    memory = AllpassC.ar(memory, 0.3, memo.linlin(0, 1, 0.03, 0.2), memo * 2);
    memory = AllpassC.ar(memory, 0.3, memo.linlin(0, 1, 0.05, 0.15), memo * 1.5);
    memory = LPF.ar(memory, memo.linexp(0, 1, 8000, 2000));
    sig = sig + (memory * memo * 0.5);

    // Soft compression for density
    sig = sig.tanh;

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_beacon_vigil_diaspora loaded".postln;
