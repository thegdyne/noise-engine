// servo: Mechanical eyes - precise servo movements
SynthDef(\forge_ex_machina_servo, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var motor, precision, focus, track, idle;

    // Theme params
    motor = In.kr(customBus0).linlin(0, 1, 0.3, 0.9);       // P1: Motor whir
    precision = In.kr(customBus1).linlin(0, 1, 8, 35);      // P2: Movement precision
    focus = In.kr(customBus2).linlin(0, 1, 0.2, 0.6);       // P3: Focus clicks
    track = In.kr(customBus3).linlin(0, 1, 0.5, 3);         // P4: Tracking rate
    idle = In.kr(customBus4).linlin(0, 1, 0.2, 0.6);        // P5: Idle hum

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

    // DSP: Continuous idle hum (always present)
    sig = SinOsc.ar(freq * [0.5, 1]) * idle * 0.35;

    // Motor whir - continuous high frequency
    sig = sig + (BPF.ar(WhiteNoise.ar(motor * 0.5), 3000 * LFNoise1.kr(track).range(0.8, 1.2), 0.2));

    // Precision clicks - stepped movements (boosted)
    sig = sig + (Ringz.ar(Dust.ar(precision) * 0.25, freq * [4, 6, 8], 0.03) * 0.6);

    // Focus mechanism
    sig = sig + (Ringz.ar(Dust.ar(focus * 5) * 0.2, freq * 2, 0.1) * focus);

    // Tracking servo - modulated noise
    sig = sig + (BPF.ar(PinkNoise.ar(motor * 0.4), 1500 * LFNoise0.kr(track).range(0.5, 2), 0.25));

    sig = sig * 0.5;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_ex_machina_servo loaded".postln;
