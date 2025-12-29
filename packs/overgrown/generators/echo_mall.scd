SynthDef(\forge_overgrown_echo_mall, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                        filterTypeBus, envEnabledBus, envSourceBus=0,
                                        clockRateBus, clockTrigBus,
                                        midiTrigBus=0, slotIndex=0,
                                        customBus0, customBus1, customBus2, customBus3, customBus4,
                                        portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var vast, decayTime, hollow, ghost, memory;
    var source, comb1, comb2, comb3, ghostTone, memoryEcho;

    // Theme params
    vast = In.kr(customBus0);
    decayTime = In.kr(customBus1);
    hollow = In.kr(customBus2);
    ghost = In.kr(customBus3);
    memory = In.kr(customBus4);

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

    // Source - soft pulse with some noise
    source = LFPulse.ar(freq, 0, 0.3 + (hollow * 0.2)) * 0.2;
    source = source + (PinkNoise.ar(0.05) * hollow);
    source = LPF.ar(source, freq * 4);

    // Comb filter delays for cavernous space
    comb1 = CombL.ar(source, 0.5, vast.linexp(0, 1, 0.05, 0.3), decayTime.linexp(0, 1, 0.5, 4));
    comb2 = CombL.ar(source, 0.5, vast.linexp(0, 1, 0.07, 0.35), decayTime.linexp(0, 1, 0.6, 4.5));
    comb3 = CombL.ar(source, 0.5, vast.linexp(0, 1, 0.11, 0.4), decayTime.linexp(0, 1, 0.4, 3.5));

    // Ghost tones - high pitched whispers
    ghostTone = SinOsc.ar(freq * 4 * LFNoise1.kr(0.2).range(0.98, 1.02)) * ghost * 0.08;
    ghostTone = ghostTone + (SinOsc.ar(freq * 6 * LFNoise1.kr(0.15).range(0.97, 1.03)) * ghost * 0.04);
    ghostTone = ghostTone * LFNoise1.kr(0.5).range(0.3, 1);

    // Memory echoes - delayed harmonics
    memoryEcho = SinOsc.ar(freq * 2) * memory * 0.1;
    memoryEcho = DelayL.ar(memoryEcho, 1.0, memory.linexp(0, 1, 0.2, 0.8));
    memoryEcho = memoryEcho + DelayL.ar(memoryEcho * 0.5, 1.0, memory.linexp(0, 1, 0.3, 0.6));

    // Combine with stereo spread
    sig = [comb1 + (comb3 * 0.5), comb2 + (comb3 * 0.5)];
    sig = sig + ghostTone + memoryEcho;

    // Hollow filtering
    sig = HPF.ar(sig, hollow.linexp(0, 1, 80, 300));

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_overgrown_echo_mall loaded".postln;
