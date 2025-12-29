SynthDef(\forge_backyard_dig, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var spade, soil, stone, digDepth, effort;
    var spadeHit, soilMove, stoneClunk, earthThud, effortBreath;
    var digTrig, digRate, modIndex;

    // Theme params
    spade = In.kr(customBus0);
    soil = In.kr(customBus1);
    stone = In.kr(customBus2);
    digDepth = In.kr(customBus3);
    effort = In.kr(customBus4);

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

    // Digging rate
    digRate = effort.linexp(0, 1, 0.5, 3);
    digTrig = Dust.ar(digRate);

    // Spade hit - FM metallic clang
    modIndex = spade.linlin(0, 1, 2, 8);
    spadeHit = SinOsc.ar(
        freq * 2.5 + (SinOsc.ar(freq * 7.1, 0, freq * modIndex) * Decay.ar(digTrig, 0.1)),
        0,
        Decay2.ar(digTrig, 0.002, 0.08)
    );
    spadeHit = spadeHit * spade * 0.4;

    // Soil movement - granular texture
    soilMove = PinkNoise.ar(0.3) * Decay.ar(digTrig, soil.linlin(0, 1, 0.1, 0.3));
    soilMove = LPF.ar(soilMove, soil.linexp(0, 1, 800, 2500));
    soilMove = soilMove * soil * 0.4;

    // Stone clunk - occasional hard impact
    stoneClunk = Dust.ar(digRate * stone * 0.5);
    stoneClunk = SinOsc.ar(
        freq * 1.5 + (SinOsc.ar(freq * 3.2, 0, freq * 4) * Decay.ar(stoneClunk, 0.05)),
        0,
        Decay2.ar(stoneClunk, 0.001, 0.06)
    );
    stoneClunk = stoneClunk + (BrownNoise.ar(0.2) * Decay.ar(Dust.ar(digRate * stone * 0.5), 0.03));
    stoneClunk = stoneClunk * stone * 0.5;

    // Earth thud - low body of dig
    earthThud = BrownNoise.ar(0.4) * Decay.ar(digTrig, 0.12);
    earthThud = LPF.ar(earthThud, digDepth.linexp(0, 1, 150, 400));
    earthThud = earthThud * digDepth * 0.4;

    // Effort breath - exertion sounds
    effortBreath = PinkNoise.ar(0.15);
    effortBreath = BPF.ar(effortBreath, 800, 0.6);
    effortBreath = effortBreath * LFNoise1.kr(effort.linlin(0, 1, 0.5, 2)).range(0, 1);
    effortBreath = effortBreath * effort * 0.25;

    // Mix all components
    sig = spadeHit + soilMove + stoneClunk + earthThud + effortBreath;

    // Continuous bed for drone stability - earth/soil ambience
    sig = sig + (BrownNoise.ar(0.06) + PinkNoise.ar(0.03));

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_backyard_dig loaded".postln;
