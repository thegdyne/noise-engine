// mist_drift: Morning mist - evolving filtered noise
SynthDef(\forge_hoar_frost_mist_drift, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var density, drift, color, width, breath;

    // Theme params
    density = In.kr(customBus0).linlin(0, 1, 0.5, 1);
    drift = In.kr(customBus1).linlin(0, 1, 0.02, 0.3);
    color = In.kr(customBus2).linexp(0, 1, 400, 3000);
    width = In.kr(customBus3).linlin(0, 1, 0.3, 1.5);
    breath = In.kr(customBus4).linlin(0, 1, 0, 0.6);

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

    // DSP: Filtered noise with slow drift - wider filter, more gain
    sig = PinkNoise.ar(density) + (BrownNoise.ar(density * 0.3));
    sig = BPF.ar(sig,
        color * LFNoise1.kr(drift).exprange(0.7, 1.4),
        width
    ) * 8;

    // Add breathy tonal element
    sig = sig + (SinOsc.ar(freq * [1, 1.002]) * breath * LFNoise1.kr(drift * 0.5).range(0.3, 1) * 0.5);

    sig = sig * 0.5;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_hoar_frost_mist_drift loaded".postln;
