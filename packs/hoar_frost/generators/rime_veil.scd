// rime_veil: Crystalline frost forming - shimmering high harmonics
SynthDef(\forge_hoar_frost_rime_veil, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var shimmer, density, brightness, spread, drift;

    // Theme params
    shimmer = In.kr(customBus0).linlin(0, 1, 0.1, 4);      // P1: Shimmer rate
    density = In.kr(customBus1).linlin(0, 1, 0.3, 1);      // P2: Harmonic density (amplitude rolloff)
    brightness = In.kr(customBus2).linlin(0, 1, 0.3, 1);   // P3: High partial level
    spread = In.kr(customBus3).linlin(0, 1, 0, 0.02);      // P4: Stereo spread
    drift = In.kr(customBus4).linlin(0, 1, 0, 0.01);       // P5: Pitch drift

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

    // DSP: Additive harmonics with shimmer (fixed 12 partials, density controls rolloff)
    sig = Mix.fill(12, { |i|
        var partial = i + 1;
        var partialFreq = freq * partial * (1 + (LFNoise1.kr(drift * partial) * drift));
        var partialAmp = (1 / partial.sqrt) * (density ** (i / 6)) * (brightness ** (i / 12));
        var shimmerMod = SinOsc.kr(shimmer * (1 + (i * 0.1)), Rand(0, 2pi)).range(0.5, 1);
        SinOsc.ar(partialFreq, 0, partialAmp * shimmerMod * 0.1)
    });

    // Stereo spread
    sig = Splay.ar(sig.dup(2), spread);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_hoar_frost_rime_veil loaded".postln;
