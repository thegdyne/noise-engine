SynthDef(\forge_moss_root_lichen_bell, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                          filterTypeBus, envEnabledBus, envSourceBus=0,
                                          clockRateBus, clockTrigBus,
                                          midiTrigBus=0, slotIndex=0,
                                          customBus0, customBus1, customBus2, customBus3, customBus4,
                                          portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var stone, ring, crust, age, spot;
    var exciter, modes, crustNoise, spotPartial;
    var modeRatios, modeAmps, ringTime;

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
    stone = In.kr(customBus0);
    ring = In.kr(customBus1);
    crust = In.kr(customBus2);
    age = In.kr(customBus3);
    spot = In.kr(customBus4);

    // Exciter: stone-like impulse
    exciter = Mix([
        HPF.ar(WhiteNoise.ar, stone.linexp(0, 1, 1000, 5000)),
        Impulse.ar(0) * 0.5
    ]) * EnvGen.ar(Env.perc(0.001, stone.linexp(0, 1, 0.01, 0.05)));

    // Ring time based on ring parameter
    ringTime = ring.linexp(0, 1, 0.3, 4);

    // Modal ratios - inharmonic for bell-like character, age adds stretch
    modeRatios = [1, 2.32, 3.56, 4.87, 6.23, 7.89] * (1 + (age * 0.1 * Array.series(6, 0, 0.02)));
    modeAmps = [1, 0.6, 0.4, 0.25, 0.15, 0.1];

    // Modal synthesis
    modes = Mix(Array.fill(6, { |i|
        var modeFreq = freq * modeRatios[i];
        var modeDecay = ringTime / (1 + (i * 0.3));
        Ringz.ar(exciter, modeFreq.clip(20, 15000), modeDecay) * modeAmps[i]
    })) * 0.3;

    // Add fundamental sine for body
    modes = modes + (SinOsc.ar(freq) * EnvGen.ar(Env.perc(0.001, ringTime * 0.5)) * 0.2);

    sig = modes;

    // Crust: textural noise layer
    crustNoise = BPF.ar(
        GrayNoise.ar,
        freq * 4,
        0.3
    ) * EnvGen.ar(Env.perc(0.01, crust.linexp(0, 1, 0.05, 0.3))) * crust * 0.2;
    sig = sig + crustNoise;

    // Spot: emphasized bright partial
    spotPartial = SinOsc.ar(freq * 5.5) * EnvGen.ar(Env.perc(0.001, ringTime * 0.3)) * spot * 0.15;
    sig = sig + spotPartial;

    // Subtle stereo from age-induced detuning
    sig = ~stereoSpread.(sig, 0.15, age.linlin(0, 1, 0.2, 0.5));

    // MANDATORY output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_moss_root_lichen_bell loaded".postln;
