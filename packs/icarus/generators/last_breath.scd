// Last Breath -- human fragility, heartbeat and breath
// Role: foreground

SynthDef(\forge_icarus_last_breath, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                       filterTypeBus, envEnabledBus, envSourceBus=0,
                                       clockRateBus, clockTrigBus,
                                       midiTrigBus=0, slotIndex=0,
                                       customBus0, customBus1, customBus2, customBus3, customBus4,
                                       portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var heart, breath, fear, flesh, final;
    var pulse, inhale, tremble, body, heartTrig;

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
    heart = In.kr(customBus0).linlin(0, 1, 0.8, 3);      // Heart rate Hz (48-180 bpm)
    breath = In.kr(customBus1).linlin(0, 1, 0.1, 0.5);   // Breath cycle Hz
    fear = In.kr(customBus2).linlin(0, 1, 0.0, 0.3);     // Trembling amount
    flesh = In.kr(customBus3).linlin(0, 1, 0.2, 0.8);    // Body resonance
    final = In.kr(customBus4).linlin(0, 1, 1.0, 0.3);    // Fading level

    // Fear trembling
    tremble = LFNoise2.kr(8 + (fear * 20), fear, 1);

    // Heartbeat - low thump with double-beat pattern
    heartTrig = Impulse.ar(heart) + Impulse.ar(heart, 0.3);
    pulse = SinOsc.ar(freq * 0.5 * tremble, 0, 0.6);
    pulse = pulse * Decay2.ar(heartTrig, 0.01, 0.15);

    // Breathing - filtered noise sweep
    inhale = PinkNoise.ar(0.4);
    inhale = BPF.ar(inhale, freq * SinOsc.kr(breath, 0, 0.5, 1.5), 0.3);

    // Flesh - formant resonances (organic body sound)
    body = Saw.ar(freq * tremble, flesh * 0.3);
    body = Formlet.ar(body, freq * 1.5, 0.005, 0.1);
    body = body + Formlet.ar(body, freq * 2.5, 0.005, 0.08);

    // Combine with fading
    sig = (pulse + inhale + body) * final;

    // Intimate stereo - close to the heart
    sig = ~stereoSpread.(sig, 0.05, 0.2);

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  * forge_icarus_last_breath loaded".postln;
