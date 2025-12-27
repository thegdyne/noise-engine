// mist: Fine spray from waterfall impact
SynthDef(\forge_sgwd_mist, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var spray, fine, drift, cool, veil;

    // Theme params
    spray = In.kr(customBus0).linlin(0, 1, 0.5, 1);
    fine = In.kr(customBus1).linexp(0, 1, 800, 3000);
    drift = In.kr(customBus2).linlin(0, 1, 0.1, 0.8);
    cool = In.kr(customBus3).linlin(0, 1, 0.3, 0.7);
    veil = In.kr(customBus4).linlin(0, 1, 0.4, 0.8);

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

    // DSP: Mist - continuous noise bed is key
    // Strong continuous base
    sig = PinkNoise.ar(0.5) + BrownNoise.ar(0.3);
    sig = LPF.ar(sig, 2000);

    // Spray texture
    sig = sig + BPF.ar(WhiteNoise.ar(spray * 0.4), fine, 0.5);

    // Cool air breath
    sig = sig + (LPF.ar(PinkNoise.ar(cool * 0.4), 1500));

    // Gentle drift modulation
    sig = sig * LFNoise1.kr(drift * 0.5).range(0.8, 1);

    sig = sig * 0.5;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_sgwd_mist loaded".postln;
