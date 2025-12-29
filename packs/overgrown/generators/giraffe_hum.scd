SynthDef(\forge_overgrown_giraffe_hum, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                          filterTypeBus, envEnabledBus, envSourceBus=0,
                                          clockRateBus, clockTrigBus,
                                          midiTrigBus=0, slotIndex=0,
                                          customBus0, customBus1, customBus2, customBus3, customBus4,
                                          portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var breath, throat, call, gentle, wonder;
    var source, formant1, formant2, formant3, breathNoise, vibrato, shimmer;

    // Theme params
    breath = In.kr(customBus0);
    throat = In.kr(customBus1);
    call = In.kr(customBus2);
    gentle = In.kr(customBus3);
    wonder = In.kr(customBus4);

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

    // Gentle vibrato for organic feel
    vibrato = SinOsc.kr(call.linexp(0, 1, 3, 7)).range(0.995, 1.005);

    // Source oscillator - soft saw with gentle character
    source = LFSaw.ar(freq * vibrato) * (1 - (gentle * 0.5));
    source = source + (SinOsc.ar(freq * vibrato) * gentle * 0.8);
    source = source * 0.5;

    // Formant filters - vocal throat character
    formant1 = BPF.ar(source, throat.linexp(0, 1, 300, 800), 0.15) * 4;
    formant2 = BPF.ar(source, throat.linexp(0, 1, 800, 2000), 0.12) * 3;
    formant3 = BPF.ar(source, throat.linexp(0, 1, 2000, 3500), 0.1) * 2;

    // Breath noise layer
    breathNoise = BPF.ar(PinkNoise.ar, throat.linexp(0, 1, 400, 1200), 0.4) * breath * 0.3;
    breathNoise = breathNoise * LFNoise1.kr(2).range(0.5, 1);

    // Wonder shimmer - high harmonics
    shimmer = SinOsc.ar(freq * [5.01, 4.99] * vibrato) * wonder * 0.08;
    shimmer = shimmer + (SinOsc.ar(freq * [7.02, 6.98] * vibrato) * wonder * 0.04);

    // Combine with stereo spread
    sig = [formant1 + formant2 + (formant3 * 0.5), formant1 + formant2 + (formant3 * 0.5)];
    sig = sig + breathNoise + shimmer;

    // Soft movement
    sig = Balance2.ar(sig[0], sig[1], SinOsc.kr(0.15).range(-0.3, 0.3));

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_overgrown_giraffe_hum loaded".postln;
