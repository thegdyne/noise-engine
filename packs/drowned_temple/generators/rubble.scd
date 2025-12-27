// rubble: Collapsed stone and debris
SynthDef(\forge_drowned_temple_rubble, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var crumble, impact, scatter, grind, settle;

    // Theme params
    crumble = In.kr(customBus0).linlin(0, 1, 2, 20);        // P1: Crumble rate
    impact = In.kr(customBus1).linlin(0, 1, 0.2, 0.8);      // P2: Impact weight
    scatter = In.kr(customBus2).linlin(0, 1, 5, 40);        // P3: Scatter density
    grind = In.kr(customBus3).linlin(0, 1, 0, 0.5);         // P4: Grinding friction
    settle = In.kr(customBus4).linlin(0, 1, 0.1, 0.5);      // P5: Settling dust

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

    // DSP: Stone impacts - low thuds
    sig = Ringz.ar(Dust.ar(crumble) * impact, freq * [0.5, 0.7, 1], 0.15) * 0.4;

    // Scatter - small debris
    sig = sig + (Ringz.ar(Dust.ar(scatter) * 0.15, freq * [2, 3, 4.5], 0.03) * 0.5);

    // Grinding friction
    sig = sig + (LPF.ar(Crackle.ar(1.7) * grind * 0.3, freq * 3));

    // Settling dust - continuous filtered noise
    sig = sig + (LPF.ar(PinkNoise.ar(settle), 600) * 0.4);

    sig = sig * 0.4;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_drowned_temple_rubble loaded".postln;
