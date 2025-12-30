SynthDef(\forge_tricorn_rubble, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                   filterTypeBus, envEnabledBus, envSourceBus=0,
                                   clockRateBus, clockTrigBus,
                                   midiTrigBus=0, slotIndex=0,
                                   customBus0, customBus1, customBus2, customBus3, customBus4,
                                   portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, envSource, clockRate, portamento;
    var impacts, chunks, scatter, settle, dustAmt;
    var trig, resonances, dustCloud, decayTime, freqSpread;

    // Theme params
    impacts = In.kr(customBus0);
    chunks = In.kr(customBus1);
    scatter = In.kr(customBus2);
    settle = In.kr(customBus3);
    dustAmt = In.kr(customBus4);

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

    // Trigger rate based on impacts
    trig = Dust.ar(impacts.linexp(0, 1, 1, 30));

    // Decay time based on settle
    decayTime = settle.linexp(0, 1, 0.05, 0.8);

    // Frequency spread based on chunks
    freqSpread = chunks.linlin(0, 1, 0.5, 3);

    // Multiple resonances for different debris sizes
    // Small debris - high freq
    resonances = Ringz.ar(trig, freq * (2 + (LFNoise0.kr(5) * scatter)), decayTime * 0.3, 0.2);
    resonances = resonances + Ringz.ar(trig, freq * (3 + (LFNoise0.kr(4) * scatter * freqSpread)), decayTime * 0.2, 0.15);

    // Medium chunks
    resonances = resonances + Ringz.ar(trig, freq * (1 + (LFNoise0.kr(3) * scatter * 0.5)), decayTime * 0.6, 0.25);
    resonances = resonances + Ringz.ar(trig, freq * (1.5 + (LFNoise0.kr(2) * scatter)), decayTime * 0.5, 0.2);

    // Large pieces - low freq
    resonances = resonances + Ringz.ar(trig, freq * (0.5 + (LFNoise0.kr(1) * scatter * 0.3)), decayTime, 0.3);
    resonances = resonances + Ringz.ar(trig, freq * 0.25, decayTime * 1.2, 0.2 * (1 - chunks));

    sig = resonances * 0.5;

    // Dust cloud - continuous noise layer
    dustCloud = PinkNoise.ar(0.2) + BrownNoise.ar(0.15);
    dustCloud = LPF.ar(dustCloud, freq * 2);
    dustCloud = dustCloud * LFNoise2.kr(0.5).range(0.6, 1.0);

    sig = sig + (dustCloud * (0.3 + (dustAmt * 0.7)));

    // Continuous low rumble for drone safety - boosted
    sig = sig + LPF.ar(BrownNoise.ar(0.15), 200);
    sig = sig + LPF.ar(PinkNoise.ar(0.1), freq);

    // Impact transients - filtered noise bursts
    sig = sig + (HPF.ar(PinkNoise.ar(0.3) * Decay.ar(trig, 0.02), 2000) * impacts);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, 0.2, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_tricorn_rubble loaded".postln;
