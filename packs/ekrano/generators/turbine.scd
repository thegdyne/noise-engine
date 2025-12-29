SynthDef(\forge_ekrano_turbine, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var throttle, fans, spin, roar, whine;
    var noise, lowNoise, midNoise, highNoise, spinMod, fanLayers;

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

    // Custom params
    throttle = In.kr(customBus0).linlin(0, 1, 0.1, 1.0);
    fans = In.kr(customBus1).linlin(0, 1, 0.2, 1.0);
    spin = In.kr(customBus2).linexp(0, 1, 0.5, 20);
    roar = In.kr(customBus3);
    whine = In.kr(customBus4);

    // Spin modulation - turbine wobble
    spinMod = SinOsc.kr(spin, 0, 0.1, 1);

    // Eight turbofan layers using noise bands
    lowNoise = LPF.ar(BrownNoise.ar(0.5), freq * 0.5 * spinMod) * roar;
    midNoise = BPF.ar(PinkNoise.ar(0.4), freq * spinMod, 0.3) * fans;
    highNoise = HPF.ar(WhiteNoise.ar(0.15), freq * 4 * spinMod) * whine;

    // Layer the engine bands
    fanLayers = Mix.ar([
        lowNoise * 0.6,
        midNoise * 0.8,
        highNoise * 0.4,
        BPF.ar(PinkNoise.ar(0.3), freq * 2 * spinMod, 0.2) * fans * 0.5,
        BPF.ar(WhiteNoise.ar(0.2), freq * 3, 0.15) * whine * 0.3
    ]);

    sig = fanLayers * throttle;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_ekrano_turbine loaded".postln;
