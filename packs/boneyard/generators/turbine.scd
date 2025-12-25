// TURBINE - Asymmetric rotation, worn bearings, blade harmonics
// Role: motion
SynthDef(\forge_boneyard_turbine, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                     filterTypeBus, envEnabledBus, envSourceBus=0,
                                     clockRateBus, clockTrigBus,
                                     midiTrigBus=0, slotIndex=0,
                                     customBus0, customBus1, customBus2, customBus3, customBus4,
                                     portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var blades, wear, catch, inertia, rattle;
    var rotationRate, bladeOscs, bearingNoise, windMod, rattleNoise;
    var numBlades, detunes, phases;

    // Custom params
    blades = In.kr(customBus0);     // Blade count
    wear = In.kr(customBus1);       // Bearing wear
    catch = In.kr(customBus2);      // Wind catch
    inertia = In.kr(customBus3);    // Rotational inertia
    rattle = In.kr(customBus4);     // Hub rattle

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

    // Rotation rate with inertia smoothing
    rotationRate = Lag.kr(freq, inertia.linexp(0, 1, 0.01, 2));

    // Wind catch - external modulation of rotation
    windMod = LFNoise1.kr(catch.linexp(0, 1, 0.1, 3));
    windMod = windMod * catch * 0.3;
    rotationRate = rotationRate * (1 + windMod);

    // Blade oscillators - multiple harmonics with phase rotation
    numBlades = blades.linlin(0, 1, 3, 12).round;

    // Create blade bank with wear-induced detuning
    bladeOscs = Mix.fill(8, { |i|
        var bladeFreq, bladePhase, bladeAmp, wearDetune;
        bladeFreq = rotationRate * (i + 1);
        wearDetune = LFNoise2.kr(0.5 + (i * 0.1)).range(-1, 1) * wear * 20;
        bladeFreq = bladeFreq + wearDetune;
        bladePhase = (i / 8) * 2pi;
        bladeAmp = (1 / (i + 1).sqrt) * (i < numBlades).asInteger;
        SinOsc.ar(bladeFreq, bladePhase, bladeAmp);
    });

    // Bearing noise - grindy texture proportional to wear
    bearingNoise = BPF.ar(
        GrayNoise.ar(0.5),
        rotationRate * 2,
        wear.linexp(0, 1, 0.5, 0.1)
    );
    bearingNoise = bearingNoise * wear;
    bearingNoise = bearingNoise * LFPulse.kr(rotationRate, 0, 0.3);  // Rhythmic grinding

    // Hub rattle - high frequency metallic jitter
    rattleNoise = Ringz.ar(
        Dust.ar(rotationRate * rattle.linexp(0, 1, 1, 10)),
        rotationRate * LFNoise0.kr(rotationRate).range(8, 16),
        0.01
    );
    rattleNoise = rattleNoise * rattle * 0.4;

    // Combine
    sig = (bladeOscs * 0.4) + (bearingNoise * 0.4) + rattleNoise;

    // Slight stereo rotation effect
    sig = [
        DelayN.ar(sig, 0.01, SinOsc.kr(rotationRate * 0.1).range(0, 0.005)),
        DelayN.ar(sig, 0.01, SinOsc.kr(rotationRate * 0.1, pi).range(0, 0.005))
    ];

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_boneyard_turbine loaded".postln;
