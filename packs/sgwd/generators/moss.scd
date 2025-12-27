// moss: Green mossy rock surfaces
SynthDef(\forge_sgwd_moss, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var lush, damp, soft, green, ancient;

    // Theme params
    lush = In.kr(customBus0).linlin(0, 1, 0.3, 0.8);          // P1: Density
    damp = In.kr(customBus1).linexp(0, 1, 800, 300);          // P2: Dampness (LPF)
    soft = In.kr(customBus2).linlin(0, 1, 0.2, 0.6);          // P3: Soft texture
    green = In.kr(customBus3).linlin(0, 1, 300, 600);         // P4: Green tone (BPF)
    ancient = In.kr(customBus4).linlin(0, 1, 0.1, 0.4);       // P5: Ancient drone

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

    // DSP: Soft moss texture
    // Lush filtered base
    sig = LPF.ar(PinkNoise.ar(lush), damp);
    sig = sig * LFNoise1.kr(0.3).range(0.85, 1);

    // Soft breath
    sig = sig + (LPF.ar(BrownNoise.ar(soft), 200) * SinOsc.kr(0.15).range(0.7, 1));

    // Green tone - mid frequency presence
    sig = sig + (BPF.ar(PinkNoise.ar(0.3), green, 0.4) * lush);

    // Ancient presence
    sig = sig + (SinOsc.ar(freq * [0.5, 1] * LFNoise1.kr(0.05).range(0.99, 1.01)) * ancient * 0.3).sum;

    sig = sig * 0.4;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_sgwd_moss loaded".postln;
