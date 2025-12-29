SynthDef(\forge_overgrown_rust_wind, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                        filterTypeBus, envEnabledBus, envSourceBus=0,
                                        clockRateBus, clockTrigBus,
                                        midiTrigBus=0, slotIndex=0,
                                        customBus0, customBus1, customBus2, customBus3, customBus4,
                                        portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var gust, corrosion, howl, rattle, lonely;
    var wind, resonance, rattleSound, howlTone, lonelyTone, gustMod;

    // Theme params
    gust = In.kr(customBus0);
    corrosion = In.kr(customBus1);
    howl = In.kr(customBus2);
    rattle = In.kr(customBus3);
    lonely = In.kr(customBus4);

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

    // Gust modulation - slow wind movement
    gustMod = LFNoise1.kr(gust.linexp(0, 1, 0.1, 1)).range(0.3, 1);

    // Base wind noise
    wind = PinkNoise.ar(0.3) * gustMod;
    wind = BPF.ar(wind, freq * 2 * LFNoise1.kr(0.3).range(0.8, 1.2), 0.5) * 2;
    wind = wind + (BrownNoise.ar(0.15) * gustMod);

    // Corrosion texture - grainy high frequencies
    resonance = BPF.ar(WhiteNoise.ar(0.2), freq * 4 * LFNoise1.kr(0.2).range(0.9, 1.1), 0.2) * corrosion * 3;
    resonance = resonance + (BPF.ar(WhiteNoise.ar(0.1), freq * 6, 0.15) * corrosion * 2);

    // Howling - resonant pitched wind
    howlTone = Resonz.ar(wind, freq * LFNoise1.kr(0.15).range(0.95, 1.05), howl.linexp(0, 1, 0.5, 0.1)) * howl * 4;
    howlTone = howlTone + (Resonz.ar(wind, freq * 2 * LFNoise1.kr(0.1).range(0.96, 1.04), howl.linexp(0, 1, 0.4, 0.08)) * howl * 2);

    // Rattle - triggered metallic hits
    rattleSound = Ringz.ar(Dust.ar(rattle.linexp(0, 1, 1, 15)) * 0.1, freq * [3, 5], 0.05) * rattle * 2;

    // Lonely desolate tone
    lonelyTone = SinOsc.ar(freq * 0.5 * LFNoise1.kr(0.05).range(0.98, 1.02)) * lonely * 0.15;
    lonelyTone = lonelyTone + (SinOsc.ar(freq * LFNoise1.kr(0.08).range(0.99, 1.01)) * lonely * 0.1);
    lonelyTone = lonelyTone * LFNoise1.kr(0.2).range(0.5, 1);

    // Combine with stereo
    sig = wind + resonance + howlTone + lonelyTone;
    sig = [sig + rattleSound[0], sig + rattleSound[1]];

    // Stereo wind movement
    sig = Balance2.ar(sig[0], sig[1], LFNoise1.kr(gust.linexp(0, 1, 0.1, 0.5)).range(-0.5, 0.5));

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_overgrown_rust_wind loaded".postln;
