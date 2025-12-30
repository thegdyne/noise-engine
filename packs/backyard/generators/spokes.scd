SynthDef(\forge_backyard_spokes, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var speed, density, chain, brake, freewheel;
    var spokeClick, chainRattle, brakeSqueak, freewheelTick, combFreq;

    // Theme params
    speed = In.kr(customBus0);
    density = In.kr(customBus1);
    chain = In.kr(customBus2);
    brake = In.kr(customBus3);
    freewheel = In.kr(customBus4);

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

    // Spoke clicks - metallic pings through comb filter
    spokeClick = Dust.ar(density.linexp(0, 1, 2, 40) * speed.linlin(0, 1, 0.5, 3));
    combFreq = freq * LFNoise1.kr(speed.linlin(0, 1, 0.5, 4)).range(0.98, 1.02);
    spokeClick = CombL.ar(spokeClick * 0.4, 0.05, combFreq.reciprocal.clip(0.0001, 0.05), 0.15);
    spokeClick = Ringz.ar(spokeClick, freq * [2.3, 3.7], 0.08).sum * 0.5;

    // Chain rattle - filtered noise bursts
    chainRattle = Dust.ar(speed.linexp(0, 1, 3, 25)) * WhiteNoise.ar(0.3);
    chainRattle = Ringz.ar(chainRattle, [1200, 2400, 3600], 0.02).sum;
    chainRattle = chainRattle * chain * 0.4;

    // Brake squeak - high pitched friction
    brakeSqueak = SinOsc.ar(
        freq * 8 + (LFNoise2.kr(12).range(0, 200)),
        0,
        brake * speed * 0.15 * LFNoise1.kr(3).range(0, 1)
    );

    // Freewheel clicking - rapid metallic ticks
    freewheelTick = Impulse.ar(speed.linexp(0, 1, 8, 80)) * (1 - speed).clip(0, 1);
    freewheelTick = Ringz.ar(freewheelTick * 0.2, [3000, 4500], 0.005).sum;
    freewheelTick = freewheelTick * freewheel * 0.5;

    // Mix all components
    sig = spokeClick + chainRattle + brakeSqueak + freewheelTick;

    // Add subtle continuous bed for drone stability
    sig = sig + (PinkNoise.ar(0.02) * density);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_backyard_spokes loaded".postln;
