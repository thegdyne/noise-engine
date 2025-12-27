// spire: Towering structure - hollow resonance
SynthDef(\forge_scorn_spire, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var tower, hollow, wind, creak, ancient;

    // Theme params
    tower = In.kr(customBus0).linlin(0, 1, 0.4, 1);         // P1: Tower presence
    hollow = In.kr(customBus1).linlin(0, 1, 0.015, 0.08);   // P2: Hollow depth
    wind = In.kr(customBus2).linlin(0, 1, 0.3, 0.8);        // P3: Wind through
    creak = In.kr(customBus3).linlin(0, 1, 1, 6);           // P4: Structural creak
    ancient = In.kr(customBus4).linlin(0, 1, 0.2, 0.6);     // P5: Ancient presence

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

    // DSP: Continuous tower body tone (always present)
    sig = Saw.ar(freq * [1, 1.002]) * tower * 0.3;

    // Ancient presence - deep drone (boosted)
    sig = sig + (SinOsc.ar(freq * [0.25, 0.5] * LFNoise1.kr(0.05).range(0.98, 1.02)) * ancient * 0.35);

    // Hollow resonance - comb delay
    sig = sig + CombL.ar(PinkNoise.ar(tower * 0.35), 0.1, hollow, 1.8);

    // Wind through structure (boosted)
    sig = sig + (BPF.ar(PinkNoise.ar(wind * 0.6), freq * [2, 3, 5] * LFNoise1.kr(0.2).range(0.9, 1.1), 0.2));

    // Structural creak (boosted)
    sig = sig + (Ringz.ar(Dust.ar(creak) * 0.2, freq * [0.5, 1, 1.5], 0.25) * tower * 0.5);

    sig = sig * 0.45;

    // Output chain (with Limiter for comb)
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_scorn_spire loaded".postln;
