// chain: Gold chain shimmer and clink
SynthDef(\forge_bed_stuy_chain, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var shine, weight, clink, swing, ice;

    // Theme params
    shine = In.kr(customBus0).linlin(0, 1, 0.3, 0.9);       // P1: Shine brightness
    weight = In.kr(customBus1).linlin(0, 1, 0.2, 0.7);      // P2: Chain weight
    clink = In.kr(customBus2).linlin(0, 1, 5, 25);          // P3: Clink rate (boosted)
    swing = In.kr(customBus3).linlin(0, 1, 0.2, 0.6);       // P4: Swing modulation
    ice = In.kr(customBus4).linlin(0, 1, 0.1, 0.5);         // P5: Diamond sparkle

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

    // DSP: Continuous metallic shimmer bed (always present)
    sig = BPF.ar(PinkNoise.ar(shine * 0.4), freq * 8, 0.15);

    // Metallic clinks - high harmonics (boosted)
    sig = sig + (Ringz.ar(Dust.ar(clink) * 0.25, freq * [6, 8, 10, 12], 0.1) * shine * 0.6);

    // Weight - lower body
    sig = sig + (Ringz.ar(Dust.ar(clink * 0.7) * 0.2, freq * [1.5, 2], 0.12) * weight);

    // Swing modulation on continuous bed
    sig = sig * (1 + (SinOsc.kr(swing * 3).range(0, 0.3)));

    // Ice sparkle - very high continuous shimmer
    sig = sig + (BPF.ar(WhiteNoise.ar(ice * 0.25), freq * 16, 0.1));

    sig = sig * 0.5;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_bed_stuy_chain loaded".postln;
