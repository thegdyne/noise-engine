SynthDef(\forge_avebury_carved, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                   filterTypeBus, envEnabledBus, envSourceBus=0,
                                   clockRateBus, clockTrigBus,
                                   midiTrigBus=0, slotIndex=0,
                                   customBus0, customBus1, customBus2, customBus3, customBus4,
                                   portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, envSource, clockRate, portamento;
    var marks, depthParam, bark, letter, memory;
    var trig, resonances, barkNoise, decayTime, scrapes;

    // Theme params
    marks = In.kr(customBus0);
    depthParam = In.kr(customBus1);
    bark = In.kr(customBus2);
    letter = In.kr(customBus3);
    memory = In.kr(customBus4);

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

    // Carving trigger rate
    trig = Dust.ar(marks.linexp(0, 1, 2, 25));

    // Decay time for memory
    decayTime = memory.linexp(0, 1, 0.1, 0.8);

    // Resonances - carved letter shapes at varying pitches
    resonances = Ringz.ar(trig, freq * (1 + (LFNoise0.kr(3) * letter * 0.3)), decayTime, 0.25 * depthParam);
    resonances = resonances + Ringz.ar(trig, freq * 2 * (1 + (LFNoise0.kr(2) * letter * 0.2)), decayTime * 0.6, 0.2 * depthParam);
    resonances = resonances + Ringz.ar(trig, freq * 0.5, decayTime * 1.2, 0.2 * depthParam);
    resonances = resonances + Ringz.ar(trig, freq * 3 * (1 + (LFNoise0.kr(4) * letter * 0.15)), decayTime * 0.4, 0.15 * depthParam);

    sig = resonances;

    // Bark surface texture - continuous crackle (always present)
    barkNoise = Crackle.ar(1.6 + (bark * 0.3), 0.2 + (bark * 0.15));
    barkNoise = BPF.ar(barkNoise, freq * 1.5, 0.5) * 2;
    sig = sig + barkNoise;

    // Scrape transients
    scrapes = HPF.ar(PinkNoise.ar(0.3) * Decay.ar(trig, 0.03), 3000);
    sig = sig + (scrapes * marks * 0.4);

    // Strong continuous bed for drone safety
    sig = sig + LPF.ar(PinkNoise.ar(0.25), 600);
    sig = sig + BPF.ar(BrownNoise.ar(0.3), freq, 0.4) * 3;
    sig = sig + LPF.ar(BrownNoise.ar(0.15), 200);

    // Memory echo
    sig = sig + AllpassC.ar(sig, 0.5, memory.linlin(0, 1, 0.1, 0.35), memory * 2, 0.3);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, 0.2, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_avebury_carved loaded".postln;
