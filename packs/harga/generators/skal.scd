SynthDef(\forge_harga_skal, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var oscA, oscB, xmod, xret, rungle;
    var oscAMod, oscBMod, xmodMod, xretMod, rungleMod;
    var voiceA, voiceB, toast, gather, strike;

    // Read custom params - Benjolin cross-mod structure
    oscA = In.kr(customBus0);      // P1: Osc A cup ring - influenced by xret return
    oscB = In.kr(customBus1);      // P2: Osc B table thud - scaled by rungle chaos
    xmod = In.kr(customBus2);      // P3: Cross-mod clink depth - feeds back through oscA
    xret = In.kr(customBus3);      // P4: Cross-mod echo return - shapes oscB curve
    rungle = In.kr(customBus4);    // P5: Rungle revelry chaos - reshapes toast network

    // BENJOLIN CROSS-MOD: Communal toast network
    oscAMod = oscA * (0.4 + (xret * 0.6)) * (1 + (rungle * 0.25));
    oscBMod = oscB * (0.35 + (rungle * 0.65)) * (1 + (xmod * 0.2));
    xmodMod = xmod * (1 + (oscA * oscB * 0.45));
    xretMod = xret * (1 + (oscB * rungle * 0.35));
    rungleMod = rungle * (1 + (xmod * xret * 0.3));

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
    ampVal = In.kr(~params[\amplitude]);

    // DSP: Toast pulse with membrane cross-mod
    
    // Strike trigger - continuous
    strike = Dust.ar(oscAMod.linexp(0, 1, 2, 12) * [1, 1.1]) + (Impulse.ar(0) * 0.5);
    
    // Voice A: Cup ring - metallic membrane
    voiceA = Ringz.ar(
        strike,
        freq * oscAMod.linlin(0, 1, 2, 5) * [1, 1.5, 2.2, 3.1],
        xmodMod.linlin(0, 1, 0.05, 0.2)
    ).sum * 0.25;
    voiceA = voiceA + (SinOsc.ar(freq * 2, 0, 0.1) * Decay.ar(strike.sum, 0.15));
    
    // Voice B: Table thud - wooden membrane
    voiceB = Ringz.ar(
        strike * 0.8,
        freq * oscBMod.linlin(0, 1, 0.5, 1.5) * [1, 1.3, 1.7],
        xretMod.linlin(0, 1, 0.08, 0.25)
    ).sum * 0.3;
    voiceB = voiceB + (BrownNoise.ar(0.15) * Decay.ar(strike.sum, 0.1));
    
    // Cross-mod: Cup and table interact
    voiceA = voiceA * (1 + (voiceB * xmodMod * 0.3));
    voiceB = voiceB * (1 + (voiceA * xretMod * 0.25));
    
    // Toast: Sustained resonance between strikes
    toast = SinOsc.ar(freq * [1, 1.5], 0, [0.12, 0.08]).sum;
    toast = toast * (1 + (LFNoise1.kr(rungleMod * 2 + 0.2) * 0.15));
    
    // Gather: Low communal drone
    gather = LFTri.ar(freq * 0.5, 0, 0.1);
    gather = gather + (Pulse.ar(freq * 0.25, 0.4, 0.06) * oscBMod);
    
    sig = voiceA + voiceB + (toast * (1 - (rungleMod * 0.4))) + (gather * rungleMod);
    
    // Revelry modulation
    sig = sig * (1 + (SinOsc.kr(oscAMod * 3 + 0.5) * xretMod * 0.12));
    
    // Room resonance
    sig = sig + (CombL.ar(sig, 0.1, xmodMod.linlin(0, 1, 0.03, 0.08), rungleMod * 0.4) * 0.15);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_harga_skal loaded".postln;
