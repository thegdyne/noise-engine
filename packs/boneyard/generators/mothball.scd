// MOTHBALL - Preservation wrap tension, sealed air, plastic membrane
// Role: bed
SynthDef(\forge_boneyard_mothball, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                      filterTypeBus, envEnabledBus, envSourceBus=0,
                                      clockRateBus, clockTrigBus,
                                      midiTrigBus=0, slotIndex=0,
                                      customBus0, customBus1, customBus2, customBus3, customBus4,
                                      portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var tension, pocket, seal, humid, age;
    var membrane, airPocket, leakHiss, humidChorus, ageDegradation;

    // Custom params
    tension = In.kr(customBus0);    // Wrap tension
    pocket = In.kr(customBus1);     // Air pocket
    seal = In.kr(customBus2);       // Seal integrity
    humid = In.kr(customBus3);      // Humidity
    age = In.kr(customBus4);        // Material age

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

    // Membrane drone - plastic wrap resonance
    membrane = Mix.fill(4, { |i|
        var memFreq = freq * (1 + (i * tension.linlin(0, 1, 0.5, 2)));
        var memAmp = 1 / (i + 1);
        SinOsc.ar(memFreq, i * 0.5, memAmp);
    });

    // Tension affects brightness
    membrane = membrane + (
        Pulse.ar(freq * tension.linexp(0, 1, 1, 4), 0.5, tension * 0.2)
    );

    // Air pocket - resonant bubbling
    airPocket = SinOsc.ar(
        freq * 0.5 * LFNoise2.kr(pocket.linexp(0, 1, 0.2, 2)).range(0.8, 1.2),
        0,
        0.3
    );
    airPocket = airPocket * (1 + (LFPulse.kr(pocket.linexp(0, 1, 0.5, 4), 0, 0.3) * 0.5));
    airPocket = airPocket * pocket;

    // Seal leak - filtered hiss based on seal integrity (low seal = more leak)
    leakHiss = BPF.ar(
        PinkNoise.ar(0.3),
        freq * 4,
        0.3
    );
    leakHiss = leakHiss * LFNoise2.kr(2).range(0.3, 1);
    leakHiss = leakHiss * (1 - seal) * 0.4;

    // Humidity chorus - detuning effect
    humidChorus = Mix.fill(3, { |i|
        var detune = LFNoise1.kr(0.3 + (i * 0.1)).range(-1, 1) * humid * 5;
        SinOsc.ar(freq + detune, i * 2pi/3, 0.15);
    });
    humidChorus = humidChorus * humid;

    // Combine base layers
    sig = (membrane * 0.4) + airPocket + leakHiss + humidChorus;

    // Age degradation - adds noise and reduces high frequencies
    ageDegradation = sig * LFNoise2.kr(age.linexp(0, 1, 0.1, 3)).range(0.7, 1);
    ageDegradation = LPF.ar(ageDegradation, age.linexp(0, 1, 10000, 2000));
    ageDegradation = ageDegradation + (BrownNoise.ar(age * 0.1));

    sig = ageDegradation;

    // Subtle stereo width
    sig = [
        sig + (LFNoise2.ar(0.5) * 0.02),
        DelayN.ar(sig, 0.03, 0.015) + (LFNoise2.ar(0.5) * 0.02)
    ];

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_boneyard_mothball loaded".postln;
