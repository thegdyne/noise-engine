SynthDef(\forge_fuego_celeste_magma_drone, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                              filterTypeBus, envEnabledBus, envSourceBus=0,
                                              clockRateBus, clockTrigBus,
                                              midiTrigBus=0, slotIndex=0,
                                              customBus0, customBus1, customBus2, customBus3, customBus4,
                                              portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var depth, churn, heat, pressure, rumble;
    var baseFreq, churnLFO, heatDrive, subOsc, chaosOsc, rumbleNoise, mixed;

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

    // Theme parameters
    depth = In.kr(customBus0);      // 0=surface, 1=deep earth
    churn = In.kr(customBus1);      // magma movement rate
    heat = In.kr(customBus2);       // harmonic brightness
    pressure = In.kr(customBus3);   // density/weight
    rumble = In.kr(customBus4);     // low tremor

    // Derive base frequency - depth pulls it lower
    baseFreq = freq * depth.linexp(0, 1, 1.0, 0.25);

    // Churning movement - slow chaotic LFO
    churnLFO = LFNoise1.kr(churn.linexp(0, 1, 0.05, 2.0)).range(0.97, 1.03);

    // Main oscillator - thick detuned saws at sub frequencies
    subOsc = Mix([
        LFSaw.ar(baseFreq * churnLFO * 0.5, 0, 0.4),
        LFSaw.ar(baseFreq * churnLFO * 0.502, 0, 0.3),
        LFSaw.ar(baseFreq * churnLFO * 1.0, 0, 0.2),
        LFPulse.ar(baseFreq * churnLFO * 0.25, 0, 0.7, 0.3)
    ]);

    // Chaos oscillator - adds organic movement
    chaosOsc = Crackle.ar(pressure.linlin(0, 1, 1.5, 1.95)) * 0.15;
    chaosOsc = LPF.ar(chaosOsc, baseFreq * 4);

    // Rumble - very low frequency noise
    rumbleNoise = LFNoise1.ar(baseFreq * 0.5) * rumble;
    rumbleNoise = LPF.ar(rumbleNoise, 80);

    // Mix sources
    mixed = (subOsc * 0.6) + (chaosOsc * pressure) + (rumbleNoise * 0.4);

    // Heat - adds harmonics via soft saturation
    heatDrive = heat.linexp(0, 1, 1.0, 8.0);
    mixed = (mixed * heatDrive).tanh / heatDrive.sqrt;

    // Add some slow stereo movement
    sig = mixed;

    // Standard post-chain
    sig = ~stereoSpread.(sig, churn.linlin(0, 1, 0.1, 0.4), 0.3);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;
"  * forge_fuego_celeste_magma_drone loaded".postln;
