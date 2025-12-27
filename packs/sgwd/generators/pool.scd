// pool: Dark reflective pool beneath falls
SynthDef(\forge_sgwd_pool, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var depth, dark, ripple, still, reflect;

    // Theme params
    depth = In.kr(customBus0).linlin(0, 1, 0.5, 2);           // P1: Pool depth (decay)
    dark = In.kr(customBus1).linexp(0, 1, 200, 80);           // P2: Dark water tone (LPF)
    ripple = In.kr(customBus2).linlin(0, 1, 0.5, 4);          // P3: Surface ripples
    still = In.kr(customBus3).linlin(0, 1, 0.3, 0.9);         // P4: Stillness factor
    reflect = In.kr(customBus4).linlin(0, 1, 0.1, 0.4);       // P5: Shimmer

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

    // DSP: Deep dark pool
    // Deep sub drone
    sig = SinOsc.ar(freq * 0.5 * LFNoise1.kr(0.1).range(0.99, 1.01)) * 0.4;
    sig = sig + (LFTri.ar(freq * 0.25) * 0.2);

    // Dark filtered noise bed
    sig = sig + (LPF.ar(BrownNoise.ar(0.3), dark) * still);

    // Gentle ripples
    sig = sig + (Ringz.ar(Dust.ar(ripple) * 0.15, freq * [1, 2, 3], depth * 0.3).sum);

    // Reflective shimmer
    sig = sig + (SinOsc.ar(freq * [4, 5, 6] * LFNoise1.kr(0.2).range(0.98, 1.02)) * reflect * 0.1).sum;

    sig = sig * 0.4;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_sgwd_pool loaded".postln;
