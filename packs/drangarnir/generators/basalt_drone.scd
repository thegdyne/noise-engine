// Basalt Drone - The deep resonance of ancient cliffs
// Massive detuned oscillators with minimal movement

SynthDef(\forge_drangarnir_basalt_drone, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                            filterTypeBus, envEnabledBus, envSourceBus=0,
                                            clockRateBus, clockTrigBus,
                                            midiTrigBus=0, slotIndex=0,
                                            customBus0, customBus1, customBus2, customBus3, customBus4,
                                            portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var depth, layers, cracks, rumble, stillness;
    var fundamental, harmonics, crackNoise, subRumble;
    var driftRate;

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

    // Theme params
    depth = In.kr(customBus0);
    layers = In.kr(customBus1);
    cracks = In.kr(customBus2);
    rumble = In.kr(customBus3);
    stillness = In.kr(customBus4);

    // Drift rate inversely proportional to stillness
    driftRate = stillness.linexp(0, 1, 0.3, 0.02);

    // Fundamental - deep sine with subtle waveshaping
    fundamental = SinOsc.ar(freq * depth.linlin(0, 1, 1, 0.25));
    fundamental = (fundamental * 1.2).tanh; // subtle saturation

    // Harmonic layers - geological strata
    harmonics = Mix.fill(5, { |i|
        var layerFreq = freq * (i + 1) * LFNoise1.kr(driftRate).range(0.995, 1.005);
        var layerAmp = layers * (1 / (i + 2));
        SinOsc.ar(layerFreq, 0, layerAmp * 0.2);
    });

    // Cracks - inharmonic content from fractured stone
    crackNoise = Mix.fill(3, { |i|
        var crackFreq = freq * (1.3 + (i * 0.7)) * LFNoise0.kr(0.1).range(0.9, 1.1);
        SinOsc.ar(crackFreq, 0, cracks * 0.1 / (i + 1));
    });

    // Sub-bass rumble - seismic activity
    subRumble = SinOsc.ar(
        freq * 0.125 * LFNoise1.kr(driftRate * 0.5).range(0.98, 1.02),
        0,
        rumble * 0.5
    );
    subRumble = subRumble + (LFNoise1.ar(20) * rumble * 0.05);

    // Combine
    sig = fundamental + harmonics + crackNoise + subRumble;

    // Stillness affects overall movement - more stillness = less modulation
    sig = sig * (1 + (SinOsc.kr(driftRate).range(-0.05, 0.05) * (1 - stillness)));

    // Very slow stereo drift
    sig = ~stereoSpread.(sig, driftRate * 0.1, 0.2);

    // Standard output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_drangarnir_basalt_drone loaded".postln;
