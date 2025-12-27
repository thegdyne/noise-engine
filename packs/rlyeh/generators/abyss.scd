// abyss: The deep unknown - impenetrable darkness below
SynthDef(\forge_rlyeh_abyss, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var darkness, pressure, movement, cold, void;

    // Theme params
    darkness = In.kr(customBus0).linlin(0, 1, 200, 2000);  // P1: Filter darkness
    pressure = In.kr(customBus1).linlin(0, 1, 0.3, 1);     // P2: Crushing pressure
    movement = In.kr(customBus2).linlin(0, 1, 0.02, 0.2);  // P3: Slow movement rate
    cold = In.kr(customBus3).linlin(0, 1, 0, 0.4);         // P4: Cold shimmer
    void = In.kr(customBus4).linlin(0, 1, 0, 0.6);         // P5: Void noise

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

    // DSP: Deep dark pad
    sig = Pulse.ar(freq * [0.5, 0.501, 1, 1.002], LFNoise1.kr(movement).range(0.3, 0.7));
    sig = Splay.ar(sig, 0.6) * pressure;

    // Darkness filter
    sig = LPF.ar(sig, darkness * LFNoise1.kr(movement).range(0.7, 1.3));

    // Cold shimmer
    sig = sig + (SinOsc.ar(freq * [4, 5.01, 6.02]) * cold * LFNoise1.kr(movement * 2).range(0, 1) * 0.1);

    // Void noise layer
    sig = sig + (LPF.ar(PinkNoise.ar(void), darkness * 0.5) * 0.3);

    sig = sig * 0.3;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_rlyeh_abyss loaded".postln;
