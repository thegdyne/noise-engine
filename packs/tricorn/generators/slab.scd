SynthDef(\forge_tricorn_slab, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, envSource, clockRate, portamento;
    var mass, weight, stress, grit, pressure;
    var pulse1, pulse2, sub, noisemod, pwm;

    // Theme params
    mass = In.kr(customBus0);
    weight = In.kr(customBus1);
    stress = In.kr(customBus2);
    grit = In.kr(customBus3);
    pressure = In.kr(customBus4);

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

    // Pulse width modulation - slow, heavy
    pwm = LFTri.kr(0.1 + (stress * 0.3)).range(0.3, 0.7) * mass;

    // Main pulse oscillators with stress detuning
    pulse1 = Pulse.ar(freq * (1 + (stress * 0.01)), pwm.clip(0.1, 0.9), 0.4);
    pulse2 = Pulse.ar(freq * (1 - (stress * 0.01)) * 0.999, (1 - pwm).clip(0.1, 0.9), 0.4);

    // Sub harmonic for weight
    sub = Pulse.ar(freq * 0.5, 0.5, weight * 0.5);
    sub = sub + SinOsc.ar(freq * 0.25, 0, weight * 0.3);

    // Combine
    sig = pulse1 + pulse2 + sub;

    // Grit modulation - noise on amplitude
    noisemod = LFNoise1.kr(2 + (grit * 5)).range(0.8, 1.0);
    sig = sig * noisemod;

    // Add filtered noise layer for texture
    sig = sig + (BrownNoise.ar(0.15) * grit);

    // Pressure drive - soft clip
    sig = (sig * (1 + (pressure * 2))).tanh * (1 / (1 + pressure));

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, 0.2, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_tricorn_slab loaded".postln;
