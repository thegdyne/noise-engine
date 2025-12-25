// TAILFIN - Sheet metal flexing, thunder-sheet wobble
// Role: motion
SynthDef(\forge_boneyard_tailfin, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                     filterTypeBus, envEnabledBus, envSourceBus=0,
                                     clockRateBus, clockTrigBus,
                                     midiTrigBus=0, slotIndex=0,
                                     customBus0, customBus1, customBus2, customBus3, customBus4,
                                     portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var span, weather, force, attach, harmonics;
    var metalSheet, flexLFO, rattleNoise, combedMetal;

    // Custom params
    span = In.kr(customBus0);       // Fin size
    weather = In.kr(customBus1);    // Damping
    force = In.kr(customBus2);      // Wind force/flex depth
    attach = In.kr(customBus3);     // Attachment tightness
    harmonics = In.kr(customBus4);  // Harmonic complexity

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

    // Flex LFO - wobble rate based on wind force
    flexLFO = LFNoise2.kr(force.linexp(0, 1, 0.3, 5));

    // Base metal sheet - filtered noise with resonance
    metalSheet = PinkNoise.ar(0.5) + BrownNoise.ar(0.3);

    // Resonant filtering at sheet frequency
    metalSheet = BPF.ar(
        metalSheet,
        freq * span.linexp(0, 1, 2, 0.5) * (1 + (flexLFO * force * 0.2)),
        attach.linexp(0, 1, 0.3, 0.05)  // Tighter = narrower Q
    );

    // Comb filtering for metallic harmonics
    combedMetal = CombL.ar(
        metalSheet,
        0.1,
        (freq * span.linexp(0, 1, 2, 0.5)).reciprocal.clip(0.001, 0.05),
        weather.linexp(0, 1, 2, 0.2)
    );

    // Additional harmonic layers
    combedMetal = combedMetal + Mix.fill(4, { |i|
        var harmFreq = freq * span.linexp(0, 1, 2, 0.5) * (i + 2);
        var harmAmp = harmonics / (i + 1).squared;
        Ringz.ar(
            metalSheet * 0.3,
            harmFreq * (1 + (flexLFO * 0.1)),
            weather.linexp(0, 1, 0.5, 0.05),
            harmAmp
        );
    });

    // Loose attachment rattle
    rattleNoise = Dust.ar((1 - attach).linexp(0, 1, 1, 50));
    rattleNoise = Ringz.ar(rattleNoise, freq * 4, 0.01, (1 - attach) * 0.3);

    // Combine
    sig = (metalSheet * 0.3) + (combedMetal * 0.5) + rattleNoise;

    // Weather damping - high frequency rolloff
    sig = LPF.ar(sig, weather.linexp(0, 1, 8000, 2000));

    // Subtle stereo movement
    sig = [
        sig * (1 + (flexLFO * 0.1)),
        DelayN.ar(sig, 0.02, 0.01) * (1 - (flexLFO * 0.1))
    ];

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_boneyard_tailfin loaded".postln;
