// stone: Ancient rock ledge resonance
SynthDef(\forge_sgwd_stone, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var ledge, mass, wet, age, hollow;

    // Theme params
    ledge = In.kr(customBus0).linlin(0, 1, 0.3, 0.8);         // P1: Ledge resonance
    mass = In.kr(customBus1).linlin(0, 1, 0.5, 2);            // P2: Stone mass (decay)
    wet = In.kr(customBus2).linlin(0, 1, 0.2, 0.6);           // P3: Wet surface
    age = In.kr(customBus3).linlin(0, 1, 0.1, 0.4);           // P4: Weathered
    hollow = In.kr(customBus4).linlin(0, 1, 0.02, 0.08);      // P5: Hollow behind

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

    // DSP: Stone resonance
    // Deep rock drone
    sig = SinOsc.ar(freq * [0.5, 1, 1.5] * LFNoise1.kr(0.05).range(0.99, 1.01)) * [0.4, 0.3, 0.2];
    sig = sig.sum;

    // Ledge resonance - comb filtering
    sig = sig + CombL.ar(PinkNoise.ar(ledge * 0.2), 0.1, freq.reciprocal, mass);

    // Wet surface drips
    sig = sig + (Ringz.ar(Dust.ar(wet * 8) * 0.15, freq * [2, 3, 5], 0.2).sum);

    // Hollow space behind
    sig = sig + CombL.ar(sig * 0.3, 0.1, hollow, mass * 0.5);

    // Age texture
    sig = sig + (LPF.ar(BrownNoise.ar(age * 0.2), 150));

    sig = sig * 0.35;

    // Output chain (with Limiter for comb)
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_sgwd_stone loaded".postln;
