// AUTUMN - Warm organic tones amid grey
// Family: subtractive (supersaw)
// Role: foreground

SynthDef(\forge_barbican_hound_autumn, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                          filterTypeBus, envEnabledBus, envSourceBus=0,
                                          clockRateBus, clockTrigBus,
                                          midiTrigBus=0, slotIndex=0,
                                          customBus0, customBus1, customBus2, customBus3, customBus4,
                                          portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var leaf, gold, wind, fall, drift;
    var saws, sub, warmth, windMod;

    // Standard bus reads
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
    leaf = In.kr(customBus0);   // Detuning
    gold = In.kr(customBus1);   // Warmth
    wind = In.kr(customBus2);   // Modulation
    fall = In.kr(customBus3);   // Decay character
    drift = In.kr(customBus4);  // Slow movement

    // Wind modulation
    windMod = LFNoise2.kr(0.5 + (wind * 2)) * wind * 0.02;

    // Supersaw stack - 7 detuned oscillators
    saws = Mix.fill(7, { |i|
        var detune = (i - 3) * leaf.linexp(0, 1, 0.002, 0.02);
        var driftAmt = LFNoise1.kr(0.1 + (i * 0.02)) * drift * 0.005;
        Saw.ar(freq * (1 + detune + driftAmt + windMod))
    }) / 4;

    // Sub for warmth
    sub = SinOsc.ar(freq * 0.5) * gold * 0.4;

    // Combine
    sig = saws + sub;

    // Gold warmth filter - low shelf boost
    warmth = LPF.ar(sig, gold.linexp(0, 1, 3000, 1500));
    sig = sig + (warmth * gold * 0.3);

    // Fall decay shaping - gentle rolloff
    sig = LPF.ar(sig, fall.linexp(0, 1, 2000, 6000));

    // Wind breath modulation
    sig = sig * (1 + (LFNoise2.kr(1) * wind * 0.1));

    // Stereo spread
    sig = Splay.ar(Array.fill(2, { sig }), leaf * 0.8);

    // Post-chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_barbican_hound_autumn loaded".postln;
