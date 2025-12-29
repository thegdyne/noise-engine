SynthDef(\forge_ekrano_flyby, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var doppler, speed, distance, engine, width;
    var dopplerMod, fmIndex, carrier, modulator, phaseMod, panPos, distFilter;

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
    doppler = In.kr(customBus0).linexp(0, 1, 0.05, 2);
    speed = In.kr(customBus1).linlin(0, 1, 0.1, 0.5);
    distance = In.kr(customBus2);
    engine = In.kr(customBus3).linlin(0, 1, 1, 8);
    width = In.kr(customBus4);

    // Doppler pitch modulation - slow sweep up and down
    dopplerMod = LFTri.kr(doppler).range(1 - speed, 1 + speed);

    // Phase modulation FM
    fmIndex = engine;
    modulator = SinOsc.ar(freq * dopplerMod * 2) * fmIndex * freq;
    carrier = SinOsc.ar(freq * dopplerMod + modulator);

    // Add harmonics for engine richness
    phaseMod = carrier + (SinOsc.ar(freq * dopplerMod * 0.5 + (modulator * 0.5)) * 0.4);
    phaseMod = phaseMod + (SinOsc.ar(freq * dopplerMod * 3 + (modulator * 0.3)) * 0.2);

    sig = phaseMod * 0.4;

    // Distance filter - closer = brighter
    distFilter = distance.linexp(0, 1, 800, 12000);
    sig = LPF.ar(sig, distFilter);

    // Stereo panning following doppler
    panPos = LFTri.kr(doppler).range(width.neg, width);
    sig = Pan2.ar(sig, panPos);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_ekrano_flyby loaded".postln;
