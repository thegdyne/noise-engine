SynthDef(\forge_tricorn_helix, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                   filterTypeBus, envEnabledBus, envSourceBus=0,
                                   clockRateBus, clockTrigBus,
                                   midiTrigBus=0, slotIndex=0,
                                   customBus0, customBus1, customBus2, customBus3, customBus4,
                                   portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, envSource, clockRate, portamento;
    var rotation, radius, gradient, vertigo, motion;
    var modRate, modDepth, ratio, carrier, modulator, phase1, phase2;

    // Theme params
    rotation = In.kr(customBus0);
    radius = In.kr(customBus1);
    gradient = In.kr(customBus2);
    vertigo = In.kr(customBus3);
    motion = In.kr(customBus4);

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

    // Modulation parameters
    modRate = rotation.linexp(0, 1, 0.1, 4);
    modDepth = radius.linlin(0, 1, 0.5, 8);
    ratio = gradient.linlin(0, 1, 1, 4);

    // Phase modulators - spiral motion
    phase1 = SinOsc.ar(freq * ratio, 0, modDepth);
    phase1 = phase1 * LFTri.kr(modRate).range(0.3, 1.0);

    // Vertigo - chaotic phase perturbation
    phase1 = phase1 + (LFNoise2.ar(freq * 0.1) * vertigo * 2);

    // Second modulator for thickness
    phase2 = SinOsc.ar(freq * (ratio + 0.01), 0, modDepth * 0.7);
    phase2 = phase2 * LFTri.kr(modRate * 1.01).range(0.3, 1.0);

    // Carriers with phase modulation
    carrier = SinOsc.ar(freq, phase1, 0.4);
    carrier = carrier + SinOsc.ar(freq * 1.001, phase2, 0.35);

    // Motion spread - additional detuned layers
    carrier = carrier + SinOsc.ar(freq * (1 + (motion * 0.005)), phase1 * 0.8, 0.2 * motion);
    carrier = carrier + SinOsc.ar(freq * (1 - (motion * 0.005)), phase2 * 0.8, 0.2 * motion);

    sig = carrier;

    // Add sub for weight
    sig = sig + SinOsc.ar(freq * 0.5, 0, 0.15);

    // Continuous presence layer
    sig = sig + (PinkNoise.ar(0.02));

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, 0.2, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_tricorn_helix loaded".postln;
