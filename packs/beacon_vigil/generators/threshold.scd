// THRESHOLD - Liminal doorway morphing
// Source: The in-between space, neither here nor there
// Role: Foreground - melodic morphing texture

SynthDef(\forge_beacon_vigil_threshold, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                     filterTypeBus, envEnabledBus, envSourceBus=0,
                                     clockRateBus, clockTrigBus,
                                     midiTrigBus=0, slotIndex=0,
                                     customBus0, customBus1, customBus2, customBus3, customBus4,
                                     portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var gate, echo, edge, pass, dusk;
    var stateA, stateB, morph, doorway, reflections;

    // Custom params
    gate = In.kr(customBus0);  // Morph position
    echo = In.kr(customBus1);  // Reflection
    edge = In.kr(customBus2);  // Sharpness
    pass = In.kr(customBus3);  // Passage width
    dusk = In.kr(customBus4);  // Twilight character

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

    // === DSP: Threshold Liminal Space ===

    // State A: Origin - warm, grounded, simple
    stateA = SinOsc.ar(freq);
    stateA = stateA + (SinOsc.ar(freq * 0.5) * 0.4);
    stateA = stateA + (LFTri.ar(freq) * 0.2);

    // State B: Destination - bright, complex, shimmering
    stateB = Saw.ar(freq * (1 + (pass * 0.02)));
    stateB = stateB + (Pulse.ar(freq * 2, 0.3) * 0.3);
    stateB = stateB + (SinOsc.ar(freq * 3) * 0.2);
    stateB = stateB + (SinOsc.ar(freq * 5) * 0.1);
    // Shimmering detune
    stateB = stateB + (SinOsc.ar(freq * 1.005) * 0.2);

    // Morph with edge sharpness
    // Sharp edge = more sudden transition, soft = gradual
    morph = gate.pow(1 / (0.5 + (edge * 2)));

    // Doorway resonance: at threshold center, both states interfere
    doorway = (gate - 0.5).abs;
    doorway = 1 - (doorway * 2);  // Peaks at 0.5
    doorway = doorway.clip(0, 1).pow(0.5);

    // Cross-fade states
    sig = (stateA * (1 - morph)) + (stateB * morph);

    // Add interference resonance at threshold
    sig = sig + (
        Ringz.ar(
            sig * doorway * 0.3,
            freq * pass.linlin(0, 1, 1.5, 3),
            0.2
        ) * doorway * pass
    );

    // Dusk: twilight coloring - subtle FM and detuning
    sig = sig + (SinOsc.ar(freq * (1 + (SinOsc.kr(dusk * 2).range(-0.01, 0.01)))) * dusk * 0.2);
    sig = sig * (1 + (LFNoise2.kr(dusk * 3).range(-0.1, 0.1) * dusk));

    // Reflection/echo: comb resonances
    reflections = CombC.ar(sig, 0.2, 1 / (freq * 2), echo.linlin(0, 1, 0.1, 1.5));
    reflections = reflections + CombC.ar(sig, 0.2, 1 / (freq * 3), echo.linlin(0, 1, 0.05, 0.8));
    sig = sig + (reflections * echo * 0.3);

    // Gentle stereo spread based on morph position
    sig = [
        sig * (1 + ((gate - 0.5) * 0.2)),
        sig * (1 - ((gate - 0.5) * 0.2))
    ];

    // Soft clip
    sig = sig.tanh;

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_beacon_vigil_threshold loaded".postln;
