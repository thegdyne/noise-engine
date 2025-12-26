SynthDef(\forge_arctic_henge_aurora, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
    filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
    midiTrigBus=0, slotIndex=0,
    customBus0, customBus1, customBus2, customBus3, customBus4,
    portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var curtain, shimmer, drift, green, red;
    var greenBand, redBand, phases, driftMod;

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
    curtain = In.kr(customBus0);
    shimmer = In.kr(customBus1);
    drift = In.kr(customBus2);
    green = In.kr(customBus3);
    red = In.kr(customBus4);

    // Slow drift modulation
    driftMod = LFNoise1.kr(drift.linexp(0, 1, 0.02, 0.3)) * drift * 0.02;

    // Green band - lower harmonics (partials 1-4)
    greenBand = Mix.fill(4, { |i|
        var partial = i + 1;
        var shimmerRate = shimmer.linexp(0, 1, 0.1, 2) * (1 + (i * 0.2));
        var phaseMod = SinOsc.kr(shimmerRate, i * 0.5pi) * 0.5;
        var layerAmp = (curtain * 4 - i).clip(0, 1);
        SinOsc.ar(
            freq * partial * (1 + driftMod),
            phaseMod * 2pi
        ) * layerAmp * (0.3 / partial)
    }) * green;

    // Red band - upper harmonics (partials 5-10)
    redBand = Mix.fill(6, { |i|
        var partial = i + 5;
        var shimmerRate = shimmer.linexp(0, 1, 0.2, 3) * (1 + (i * 0.15));
        var phaseMod = SinOsc.kr(shimmerRate, i * 0.7pi) * 0.7;
        var layerAmp = (curtain * 6 - i).clip(0, 1);
        SinOsc.ar(
            freq * partial * (1 + (driftMod * 1.5)),
            phaseMod * 2pi
        ) * layerAmp * (0.15 / partial)
    }) * red;

    // Combine bands
    sig = greenBand + redBand;

    // Add subtle chorus for width
    sig = sig + DelayC.ar(sig, 0.03, SinOsc.kr(0.3, 0, 0.003, 0.01)) * 0.3;

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    sig = Limiter.ar(sig, 0.95);
    Out.ar(out, sig);
}).add;
"  * forge_arctic_henge_aurora loaded".postln;
