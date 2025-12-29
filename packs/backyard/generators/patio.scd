SynthDef(\forge_backyard_patio, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var roll, groove, wheel, rattle, grit;
    var wheelRumble, grooveBump, boardRattle, surfaceGrit, bumpRate;

    // Theme params
    roll = In.kr(customBus0);
    groove = In.kr(customBus1);
    wheel = In.kr(customBus2);
    rattle = In.kr(customBus3);
    grit = In.kr(customBus4);

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
    ampVal = In.kr(~params[\amplitude]);

    // Continuous wheel rumble - low filtered noise
    wheelRumble = BrownNoise.ar(0.4) + PinkNoise.ar(0.2);
    wheelRumble = LPF.ar(wheelRumble, wheel.linexp(0, 1, 80, 400));
    wheelRumble = wheelRumble * roll.linlin(0, 1, 0.3, 1);

    // Groove bumps - rhythmic impacts as wheels hit grouting
    bumpRate = roll.linexp(0, 1, 2, 12);
    grooveBump = Impulse.ar(bumpRate) + Dust.ar(bumpRate * 0.5);
    grooveBump = Ringz.ar(grooveBump * groove * 0.5, freq * [1, 1.5, 2], 0.05).sum;
    grooveBump = grooveBump + (BPF.ar(WhiteNoise.ar(1), freq * 2, 0.3) * Decay.ar(Impulse.ar(bumpRate), 0.03) * groove * 0.3);

    // Board rattle - higher frequency wood resonance
    boardRattle = WhiteNoise.ar(0.3) * LFNoise1.kr(roll.linlin(0, 1, 5, 20)).range(0.2, 1);
    boardRattle = BPF.ar(boardRattle, [800, 1200, 1800], 0.2).sum;
    boardRattle = boardRattle * rattle * roll * 0.4;

    // Surface grit - textured high frequency
    surfaceGrit = PinkNoise.ar(0.2);
    surfaceGrit = HPF.ar(surfaceGrit, 2000);
    surfaceGrit = surfaceGrit * grit * roll * 0.3;

    // Mix all components
    sig = wheelRumble + grooveBump + boardRattle + surfaceGrit;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_backyard_patio loaded".postln;
