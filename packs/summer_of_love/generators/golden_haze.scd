SynthDef(\forge_summer_of_love_golden_haze, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                                  clockRateBus, clockTrigBus,
                                                  midiTrigBus=0, slotIndex=0,
                                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var warmth, drift, haze, layers, spread;
    var saws, driftLfo, detuneAmts, hazeFreq, saturated;

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
    warmth = In.kr(customBus0);    // Even harmonics via soft saturation
    drift = In.kr(customBus1);     // Slow pitch wandering
    haze = In.kr(customBus2);      // High frequency softening
    layers = In.kr(customBus3);    // Voice count/thickness
    spread = In.kr(customBus4);    // Stereo width

    // Slow drift LFOs - different rates for organic movement
    driftLfo = LFNoise1.kr(0.1 + (drift * 0.3)) * (drift * 0.02);

    // Detune amounts for 7 voices
    detuneAmts = [-0.03, -0.02, -0.01, 0, 0.01, 0.02, 0.03];

    // Stack of detuned saws with drift
    saws = detuneAmts.collect({ |det, i|
        var voiceFreq, voiceDrift, pan;
        voiceDrift = LFNoise1.kr(0.05 + (i * 0.02)) * (drift * 0.015);
        voiceFreq = freq * (1 + det + driftLfo + voiceDrift);
        pan = (i - 3) / 3 * spread;
        Pan2.ar(Saw.ar(voiceFreq), pan)
    }).sum;

    // Layer mixing - fewer layers = thinner, more = thicker
    sig = saws * layers.linlin(0, 1, 0.4, 1.0);

    // Add sub for warmth foundation
    sig = sig + (SinOsc.ar(freq * 0.5) * warmth * 0.3);

    // Warmth saturation - soft clipping adds even harmonics
    saturated = (sig * (1 + (warmth * 2))).tanh;
    sig = XFade2.ar(sig, saturated, warmth.linlin(0, 1, -1, 0.5));

    // Haze filter - gentle lowpass that increases with haze param
    hazeFreq = haze.linexp(0, 1, 12000, 2000);
    sig = LPF.ar(sig, hazeFreq);

    // Apply standard processing chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    sig = Limiter.ar(sig, 0.95);
    Out.ar(out, sig);
}).add;
"  * forge_summer_of_love_golden_haze loaded".postln;
