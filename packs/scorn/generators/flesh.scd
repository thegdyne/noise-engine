// flesh: Organic walls - wet membrane texture
SynthDef(\forge_scorn_flesh, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var wet, membrane, squelch, warmth, breath;

    // Theme params
    wet = In.kr(customBus0).linlin(0, 1, 0.3, 0.9);         // P1: Wetness
    membrane = In.kr(customBus1).linlin(0, 1, 0.2, 0.8);    // P2: Membrane flex
    squelch = In.kr(customBus2).linlin(0, 1, 3, 20);        // P3: Squelch rate
    warmth = In.kr(customBus3).linlin(0, 1, 200, 1200);     // P4: Body warmth
    breath = In.kr(customBus4).linlin(0, 1, 0.05, 0.2);     // P5: Breathing rate

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

    // DSP: Membrane texture - continuous filtered noise
    sig = LPF.ar(BrownNoise.ar(wet * 0.5), warmth) * SinOsc.kr(breath).range(0.7, 1);

    // Wet squelch sounds
    sig = sig + (Ringz.ar(Dust.ar(squelch) * 0.2, freq * [1, 1.5, 2], 0.1) * wet * 0.4);

    // Membrane flex - low resonance
    sig = sig + (SinOsc.ar(freq * [0.5, 1] * LFNoise1.kr(0.1).range(0.98, 1.02)) * membrane * 0.3);

    // Organic warmth
    sig = sig + (LPF.ar(Pulse.ar(freq * 0.5, 0.3), warmth) * membrane * 0.2);

    sig = sig * 0.5;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_scorn_flesh loaded".postln;
