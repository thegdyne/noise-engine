SynthDef(\forge_arctic_henge_solstice, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
    filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
    midiTrigBus=0, slotIndex=0,
    customBus0, customBus1, customBus2, customBus3, customBus4,
    portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var warm, glow, horizon, dawn, patience;
    var fundamental, evenHarmonics, oddHarmonics, shimmer, spreadL, spreadR;
    var evolutionRate;

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
    warm = In.kr(customBus0);
    glow = In.kr(customBus1);
    horizon = In.kr(customBus2);
    dawn = In.kr(customBus3);
    patience = In.kr(customBus4);

    // Evolution rate
    evolutionRate = patience.linexp(0, 1, 0.02, 0.3);

    // Fundamental - warm sine
    fundamental = SinOsc.ar(freq) * 0.4;

    // Even harmonics (warmth) - 2, 4, 6, 8
    evenHarmonics = Mix.fill(4, { |i|
        var partial = (i + 1) * 2;
        var ampMod = SinOsc.kr(evolutionRate * (1 + (i * 0.3)), i * 0.5pi).range(0.3, 1);
        SinOsc.ar(freq * partial) * ampMod * warm * (0.15 / partial)
    });

    // Odd harmonics (brightness/glow) - 3, 5, 7
    oddHarmonics = Mix.fill(3, { |i|
        var partial = (i * 2) + 3;
        var ampMod = SinOsc.kr(evolutionRate * 1.3 * (1 + (i * 0.2)), i * 0.7pi).range(0.2, 1);
        SinOsc.ar(freq * partial) * ampMod * glow * (0.1 / partial)
    });

    // Dawn swell - slow amplitude modulation
    shimmer = 1 + (SinOsc.kr(dawn.linexp(0, 1, 0.01, 0.1)) * dawn * 0.3);

    sig = (fundamental + evenHarmonics + oddHarmonics) * shimmer;

    // Stereo spread - horizon width
    spreadL = sig + (DelayC.ar(sig, 0.03, LFNoise1.kr(0.2).range(0.005, 0.015)) * horizon * 0.4);
    spreadR = sig + (DelayC.ar(sig, 0.03, LFNoise1.kr(0.25).range(0.008, 0.018)) * horizon * 0.4);
    sig = [spreadL, spreadR];

    // Soft lowpass for warmth
    sig = LPF.ar(sig, glow.linexp(0, 1, 2000, 8000));

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_arctic_henge_solstice loaded".postln;
