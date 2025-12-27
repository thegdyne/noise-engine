// canopy: Lush green overhead
SynthDef(\forge_sgwd_canopy, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var leaves, rustle, filt, drip, breeze;

    // Theme params
    leaves = In.kr(customBus0).linlin(0, 1, 0.4, 0.8);
    rustle = In.kr(customBus1).linlin(0, 1, 0.5, 3);
    filt = In.kr(customBus2).linexp(0, 1, 1200, 500);
    drip = In.kr(customBus3).linlin(0, 1, 2, 12);
    breeze = In.kr(customBus4).linlin(0, 1, 0.3, 0.7);

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

    // DSP: Canopy - continuous noise base
    // Strong continuous filtered noise
    sig = LPF.ar(PinkNoise.ar(0.5), filt);
    sig = sig + BrownNoise.ar(0.25);

    // Leaf rustle texture
    sig = sig + BPF.ar(PinkNoise.ar(leaves * 0.4), 1500 * LFNoise1.kr(rustle).range(0.7, 1.3), 0.4);

    // Breeze modulation
    sig = sig * LFNoise1.kr(0.3).range(0.7, 1);
    sig = sig + (BPF.ar(WhiteNoise.ar(breeze * 0.3), 1200, 0.4));

    // Continuous drip bed
    sig = sig + (Ringz.ar(Dust.ar(drip) * 0.25, freq * [3, 4, 5], 0.12).sum);

    sig = sig * 0.45;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_sgwd_canopy loaded".postln;
