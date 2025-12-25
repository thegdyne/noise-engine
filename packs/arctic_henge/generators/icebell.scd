SynthDef(\forge_arctic_henge_icebell, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
    filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
    midiTrigBus=0, slotIndex=0,
    customBus0, customBus1, customBus2, customBus3, customBus4,
    portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var frost, crystal, chime, shatter, echo;
    var exciter, modes, shatterNoise, reflections;

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

    // Theme params
    frost = In.kr(customBus0);
    crystal = In.kr(customBus1);
    chime = In.kr(customBus2);
    shatter = In.kr(customBus3);
    echo = In.kr(customBus4);

    // Exciter - bright impulse
    exciter = Impulse.ar(0) + (WhiteNoise.ar * EnvGen.ar(Env.perc(0.001, 0.02)) * shatter * 0.5);

    // Inharmonic crystal ratios (ice doesn't ring harmonically)
    modes = Mix.fill(8, { |i|
        var modeAmp = (chime * 8 - i).clip(0, 1);
        var inharmonic = crystal.linlin(0, 1, 0, 0.1);
        var ratio = [1, 1.47, 2.09, 2.56, 3.24, 4.13, 4.85, 5.73].at(i);
        var modeFreq = freq * (ratio + (inharmonic * i * 0.1));
        var brightness = frost.linexp(0, 1, 0.3, 2);
        var decayTime = echo.linexp(0, 1, 0.5, 4) / (i + 1).sqrt;
        Ringz.ar(
            exciter,
            (modeFreq * brightness).min(14000),
            decayTime
        ) * modeAmp * (0.2 / (i + 1).sqrt)
    });

    // Shatter transient - white noise burst
    shatterNoise = HPF.ar(
        WhiteNoise.ar * EnvGen.ar(Env.perc(0.001, 0.05 + (shatter * 0.05))),
        frost.linexp(0, 1, 2000, 6000)
    ) * shatter * 0.3;

    // Echo reflections - subtle delays
    reflections = CombL.ar(modes * 0.3, 0.2, echo.linlin(0, 1, 0.03, 0.15), echo * 2);

    sig = modes + shatterNoise + reflections;

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_arctic_henge_icebell loaded".postln;
