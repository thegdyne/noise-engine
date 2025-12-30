SynthDef(\forge_tricorn_ramp, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, envSource, clockRate, portamento;
    var spiral, ascent, concrete, levels, echo;
    var exciter, comb1, comb2, comb3, delayTime, feedback, driftRate;

    // Theme params
    spiral = In.kr(customBus0);
    ascent = In.kr(customBus1);
    concrete = In.kr(customBus2);
    levels = In.kr(customBus3);
    echo = In.kr(customBus4);

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

    // Exciter: filtered noise + impulse dust for concrete texture
    exciter = PinkNoise.ar(0.3) + (Dust.ar(3 + (concrete * 10)) * 0.2);
    exciter = exciter + (BrownNoise.ar(0.1) * concrete);

    // Ascending drift modulation
    driftRate = ascent.linexp(0, 1, 0.01, 0.5);
    freq = freq * LFSaw.kr(driftRate, 0).range(0.98, 1.04);

    // Comb resonator cascade - spiral levels
    delayTime = freq.reciprocal;
    feedback = spiral.linlin(0, 1, 0.3, 0.85);

    comb1 = CombL.ar(exciter, 0.1, delayTime.clip(0.001, 0.1), 0.5 + (levels * 1.5), 0.5);
    comb2 = CombL.ar(comb1, 0.1, (delayTime * 1.5).clip(0.001, 0.1), 0.3 + levels, 0.3);
    comb3 = CombL.ar(comb2, 0.1, (delayTime * 2.0).clip(0.001, 0.1), 0.2 + (levels * 0.5), 0.2);

    sig = (comb1 + comb2 + comb3) * 0.4;

    // Add echo dimension
    sig = sig + AllpassC.ar(sig, 0.5, echo.linlin(0, 1, 0.05, 0.3), echo * 2, 0.3);

    // Feedback resonance
    sig = sig + (CombC.ar(sig, 0.2, delayTime.clip(0.001, 0.2), feedback * 3) * spiral * 0.3);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, 0.2, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_tricorn_ramp loaded".postln;
