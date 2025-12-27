// hollow: Empty station void and silence
SynthDef(\forge_vapor_station_hollow, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var space, distant, lonely, concrete, wind;

    // Theme params
    space = In.kr(customBus0).linlin(0, 1, 0.3, 0.9);      // P1: Reverb space size
    distant = In.kr(customBus1).linlin(0, 1, 0.1, 0.6);    // P2: Distant sounds
    lonely = In.kr(customBus2).linlin(0, 1, 0.2, 0.7);     // P3: Lonely tone
    concrete = In.kr(customBus3).linlin(0, 1, 0.1, 0.5);   // P4: Concrete resonance
    wind = In.kr(customBus4).linlin(0, 1, 0.2, 0.6);       // P5: Night wind

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

    // DSP: Base - continuous filtered noise
    sig = LPF.ar(PinkNoise.ar(0.3), 800);

    // Large space reverb simulation via comb filters
    sig = sig + CombL.ar(sig * 0.3, 0.3, space * 0.15 + 0.05, space * 3);

    // Distant sounds - sparse impacts
    sig = sig + (Ringz.ar(Dust.ar(distant * 4) * 0.2, freq * [1, 1.5], space) * distant);

    // Lonely tone - single wavering sine (always present)
    sig = sig + (SinOsc.ar(freq * [1, 1.003] * LFNoise1.kr(0.1).range(0.99, 1.01)) * lonely * 0.25);

    // Concrete resonance - boosted
    sig = sig + (Resonz.ar(Dust.ar(concrete * 5) * 0.3, freq * [0.5, 1, 2], 0.15) * concrete * 5);

    // Night wind - continuous
    sig = sig + (BPF.ar(BrownNoise.ar(wind), 300 * LFNoise1.kr(0.05).range(0.5, 2), 0.6) * 0.6);

    sig = sig * 0.45;

    // Output chain (with Limiter for comb)
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_vapor_station_hollow loaded".postln;
