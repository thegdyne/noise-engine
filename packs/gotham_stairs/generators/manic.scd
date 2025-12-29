SynthDef(\forge_gotham_stairs_manic, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var hysteria, laugh, twitch, spiral, breakPoint;
    var fbOsc, modOsc, modFreq, fbAmount, chaosLFO;

    // Theme params
    hysteria = In.kr(customBus0);
    laugh = In.kr(customBus1);
    twitch = In.kr(customBus2);
    spiral = In.kr(customBus3);
    breakPoint = In.kr(customBus4);

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

    // Spiral pitch drift - slow descent
    freq = freq * (1 - (spiral * LFSaw.kr(0.1).range(0, 0.3)));

    // Manic laughter modulation - irregular tremolo
    chaosLFO = LFNoise2.kr(laugh.linlin(0, 1, 2, 15)).range(0.5, 1);
    chaosLFO = chaosLFO * (1 + (LFPulse.kr(laugh.linlin(0, 1, 4, 20), 0, 0.3) * 0.3));

    // Feedback amount with breaking point chaos
    fbAmount = hysteria.linlin(0, 1, 0.2, pi);
    fbAmount = fbAmount * (1 + (breakPoint * LFNoise0.kr(8).range(0, 0.5)));

    // FM modulator with twitchy index
    modFreq = freq * (2 + (twitch * LFNoise1.kr(5).range(0, 1)));
    modOsc = SinOsc.ar(modFreq) * freq * twitch.linlin(0, 1, 1, 8);

    // Main feedback FM oscillator
    fbOsc = SinOscFB.ar(freq + modOsc, fbAmount);

    // Layer with slightly detuned chaotic copy
    sig = fbOsc + (SinOscFB.ar(freq * 1.003 + (modOsc * 0.7), fbAmount * 0.8) * 0.5);

    // Apply manic modulation
    sig = sig * chaosLFO;

    // Add noise burst on breaking point
    sig = sig + (WhiteNoise.ar(0.1) * breakPoint * LFNoise0.kr(12).range(0, 1));

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_gotham_stairs_manic loaded".postln;
