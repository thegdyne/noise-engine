SynthDef(\forge_moss_root_root_drone, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                          filterTypeBus, envEnabledBus, envSourceBus=0,
                                          clockRateBus, clockTrigBus,
                                          midiTrigBus=0, slotIndex=0,
                                          customBus0, customBus1, customBus2, customBus3, customBus4,
                                          portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var age, depth, sap, grit, spread;
    var main, sub, aged, sapMod, gritSig;

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
    age = In.kr(customBus0);      // Inharmonic aging
    depth = In.kr(customBus1);    // Sub-octave mix
    sap = In.kr(customBus2);      // Slow drift
    grit = In.kr(customBus3);     // Bark texture
    spread = In.kr(customBus4);   // Stereo width

    // Sap flow: slow pitch drift
    sapMod = LFNoise1.kr(sap.linexp(0, 1, 0.02, 0.2)) * sap.linlin(0, 1, 0, 0.02);

    // Main oscillator: slightly detuned for organic feel
    main = Mix([
        Saw.ar(freq * (1 + sapMod)),
        Saw.ar(freq * 1.002 * (1 + sapMod)),
        Pulse.ar(freq * 0.999 * (1 + sapMod), 0.4) * 0.5
    ]) * 0.4;

    // Sub oscillator for depth
    sub = SinOsc.ar(freq * 0.5 * (1 + sapMod)) * depth.linlin(0, 1, 0, 0.6);

    // Age: add inharmonic partials (stretched harmonics like old wood)
    aged = Mix(Array.fill(4, { |i|
        var ratio = (i + 2) * (1 + (age * 0.1 * (i + 1).rand2));
        SinOsc.ar(freq * ratio) * (0.15 / (i + 1)) * age
    }));

    sig = main + sub + aged;

    // Grit: soft waveshaping for bark texture
    gritSig = (sig * grit.linexp(0, 1, 1, 4)).tanh;
    sig = sig.blend(gritSig, grit * 0.7);

    // Stereo spread
    sig = ~stereoSpread.(sig, spread.linlin(0, 1, 0.05, 0.3), spread);

    // MANDATORY output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_moss_root_root_drone loaded".postln;
