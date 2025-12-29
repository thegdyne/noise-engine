SynthDef(\forge_gotham_stairs_descent, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var stepRate, concrete, echo, weight, irregular;
    var trig, stepTrig, impact, modes, delayedSig;

    // Theme params
    stepRate = In.kr(customBus0).linlin(0, 1, 0.5, 8);
    concrete = In.kr(customBus1);
    echo = In.kr(customBus2);
    weight = In.kr(customBus3);
    irregular = In.kr(customBus4);

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

    // Irregular step trigger with timing variation
    stepTrig = Dust.ar(stepRate * (1 + (irregular * LFNoise1.kr(2).range(0, 0.5))));

    // Impact excitation - thump of foot on concrete
    impact = stepTrig * (weight.linlin(0, 1, 0.3, 1.0));
    impact = impact + (PinkNoise.ar(0.1) * Decay.ar(stepTrig, 0.02));

    // Modal resonances of concrete steps
    modes = DynKlank.ar(
        `[
            [1, 2.3, 3.1, 4.7, 6.2],
            [1, 0.5, 0.3, 0.2, 0.1] * concrete,
            [0.3, 0.2, 0.15, 0.1, 0.08] * (1 + weight)
        ],
        impact,
        freq * 0.5,
        0,
        concrete.linlin(0, 1, 0.1, 0.4)
    );

    // Add continuous low rumble for drone compatibility
    sig = modes + (BrownNoise.ar(0.05) * weight);

    // Stairwell echo/delay
    delayedSig = CombL.ar(sig, 0.5, echo.linlin(0, 1, 0.05, 0.3), echo.linlin(0, 1, 0.5, 3));
    sig = sig + (delayedSig * echo * 0.4);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_gotham_stairs_descent loaded".postln;
