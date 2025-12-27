// neural: Processing thoughts - digital cognition
SynthDef(\forge_ex_machina_neural, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var process, spark, depth, cascade, dream;

    // Theme params
    process = In.kr(customBus0).linlin(0, 1, 10, 50);       // P1: Processing rate
    spark = In.kr(customBus1).linlin(0, 1, 0.2, 0.7);       // P2: Neural spark
    depth = In.kr(customBus2).linlin(0, 1, 0.3, 0.9);       // P3: Thought depth
    cascade = In.kr(customBus3).linlin(0, 1, 0.1, 0.6);     // P4: Cascade events
    dream = In.kr(customBus4).linlin(0, 1, 0.2, 0.6);       // P5: Dream state

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

    // DSP: Continuous processing hum (always present)
    sig = BPF.ar(WhiteNoise.ar(depth * 0.4), 4000, 0.2);
    sig = sig + (SinOsc.ar(freq * [1, 2]) * depth * 0.2);

    // Neural sparks - high frequency clicks (boosted)
    sig = sig + (Ringz.ar(Dust.ar(process) * 0.25, freq * [8, 10, 12, 16], 0.03) * spark * 0.6);

    // Thought depth - layered digital tones
    sig = sig + (Pulse.ar(freq * [1, 2, 4] * LFNoise0.kr(0.5).range(0.98, 1.02), 0.2) * depth * 0.2);

    // Cascade events - rapid sequences
    sig = sig + (Ringz.ar(Dust.ar(cascade * 40) * 0.12, freq * LFNoise0.kr(10).range(2, 8), 0.015) * cascade);

    // Dream state - soft wandering
    sig = sig + (SinOsc.ar(freq * LFNoise1.kr(0.2).range(0.5, 2)) * dream * 0.25);

    sig = sig * 0.5;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_ex_machina_neural loaded".postln;
