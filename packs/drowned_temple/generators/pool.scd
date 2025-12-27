// pool: Flooded temple floor
SynthDef(\forge_drowned_temple_pool, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var ripple, depth, drip, reflect, still;

    // Theme params
    ripple = In.kr(customBus0).linlin(0, 1, 0.1, 1);        // P1: Ripple intensity
    depth = In.kr(customBus1).linlin(0, 1, 0.3, 1);         // P2: Water depth
    drip = In.kr(customBus2).linlin(0, 1, 1, 10);           // P3: Drip rate
    reflect = In.kr(customBus3).linlin(0, 1, 0.1, 0.6);     // P4: Surface reflection
    still = In.kr(customBus4).linlin(0, 1, 0.2, 0.7);       // P5: Still water tone

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

    // DSP: Still water - filtered sine cluster
    sig = SinOsc.ar(freq * [0.5, 1, 2.01] * LFNoise1.kr(0.1).range(0.99, 1.01)) * still * 0.2;
    sig = Splay.ar(sig, 0.5);

    // Ripple modulation
    sig = sig * (1 + (SinOsc.kr(ripple * 2).range(0, 0.3)));

    // Drip impacts - stereo array
    sig = sig + (Ringz.ar(Dust.ar(drip) * 0.25, freq * [4, 6], 0.08 * depth) * reflect);

    // Deep water presence
    sig = sig + (SinOsc.ar(freq * 0.25) * depth * 0.2);

    // Surface shimmer
    sig = sig + (BPF.ar(PinkNoise.ar(reflect * 0.2), freq * 8, 0.2) * LFNoise1.kr(0.5).range(0.3, 1));

    sig = sig * 0.45;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_drowned_temple_pool loaded".postln;
