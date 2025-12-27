// frozen_breath: Cold air exhalation - breathy formants
SynthDef(\forge_hoar_frost_frozen_breath, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var airiness, formant1, formant2, breathRate, tonal;

    // Theme params
    airiness = In.kr(customBus0).linlin(0, 1, 0.3, 1);
    formant1 = In.kr(customBus1).linexp(0, 1, 400, 1800);
    formant2 = In.kr(customBus2).linexp(0, 1, 1000, 3500);
    breathRate = In.kr(customBus3).linlin(0, 1, 0.1, 0.8);
    tonal = In.kr(customBus4).linlin(0, 1, 0.1, 0.6);

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

    // DSP: Breath noise through formant filters - boosted gain
    sig = PinkNoise.ar(airiness) + (WhiteNoise.ar(airiness * 0.3));

    // Formant resonances with higher gain
    sig = Resonz.ar(sig, formant1 * LFNoise1.kr(breathRate).range(0.92, 1.08), 0.15) * 6;
    sig = sig + (Resonz.ar(PinkNoise.ar(airiness * 0.5), formant2 * LFNoise1.kr(breathRate * 0.7).range(0.92, 1.08), 0.2) * 4);

    // Add tonal undertone
    sig = sig + (SinOsc.ar(freq * [1, 2.01]) * tonal * LFNoise1.kr(breathRate).range(0.4, 1) * 0.4);

    // Breath amplitude modulation
    sig = sig * LFNoise1.kr(breathRate * 2).range(0.6, 1);

    sig = sig * 0.4;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_hoar_frost_frozen_breath loaded".postln;
