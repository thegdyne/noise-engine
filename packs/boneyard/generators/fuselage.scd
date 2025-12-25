// FUSELAGE - Hollow metallic tube resonance, struck aluminum bodies
// Role: foreground
SynthDef(\forge_boneyard_fuselage, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                      filterTypeBus, envEnabledBus, envSourceBus=0,
                                      clockRateBus, clockTrigBus,
                                      midiTrigBus=0, slotIndex=0,
                                      customBus0, customBus1, customBus2, customBus3, customBus4,
                                      portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var length, corrosion, breach, material, strike;
    var exciter, tube, modes, breachNoise;

    // Custom params
    length = In.kr(customBus0);     // Tube length resonance
    corrosion = In.kr(customBus1);  // Decay and damping
    breach = In.kr(customBus2);     // Air hole modulation
    material = In.kr(customBus3);   // Aluminum to steel
    strike = In.kr(customBus4);     // Strike position

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

    // Exciter - metallic impulse colored by material
    exciter = Impulse.ar(0) + Dust.ar(0.5);
    exciter = exciter * WhiteNoise.ar(1);
    exciter = HPF.ar(exciter, material.linexp(0, 1, 800, 3000));  // Brighter = aluminum
    exciter = LPF.ar(exciter, material.linexp(0, 1, 6000, 12000));

    // Tube resonance - comb filter bank simulating hollow body
    tube = CombL.ar(
        exciter,
        0.1,
        (freq * length.linexp(0, 1, 0.5, 2)).reciprocal.clip(0.001, 0.1),
        corrosion.linexp(0, 1, 4, 0.3)  // Higher corrosion = shorter decay
    );

    // Harmonic modes - tube has multiple resonant frequencies
    modes = Klank.ar(
        `[
            [1, 2.76, 5.4, 8.93],  // Tube mode ratios
            [1, 0.5, 0.3, 0.15] * (1 - (corrosion * 0.5)),
            [1, 0.8, 0.5, 0.3] * corrosion.linexp(0, 1, 2, 0.2)
        ],
        exciter,
        freq * length.linexp(0, 1, 0.5, 2),
        0,
        corrosion.linexp(0, 1, 3, 0.5)
    );

    // Strike position affects harmonic emphasis
    modes = modes * (1 + (SinOsc.ar(freq * strike.linlin(0, 1, 1, 4)) * 0.3));

    // Breach - air whistling through holes
    breachNoise = BPF.ar(
        PinkNoise.ar(0.3),
        freq * LFNoise1.kr(2).range(1.5, 3),
        0.1
    );
    breachNoise = breachNoise * LFNoise2.kr(5).range(0.2, 1);
    breachNoise = breachNoise * breach;

    // Combine
    sig = (tube * 0.4) + (modes * 0.5) + breachNoise;

    // Material coloring - steel is darker
    sig = LPF.ar(sig, material.linexp(0, 1, 3000, 8000));

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_boneyard_fuselage loaded".postln;
