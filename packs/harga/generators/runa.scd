SynthDef(\forge_harga_runa, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var oscA, oscB, xmod, xret, rungle;
    var oscAMod, oscBMod, xmodMod, xretMod, rungleMod;
    var voiceA, voiceB, carve, stone, syncRatio;

    // Read custom params - Benjolin cross-mod structure
    oscA = In.kr(customBus0);      // P1: Osc A master stroke - influenced by xret return
    oscB = In.kr(customBus1);      // P2: Osc B slave angle - scaled by rungle chaos
    xmod = In.kr(customBus2);      // P3: Cross-mod carve depth - feeds back through oscA
    xret = In.kr(customBus3);      // P4: Cross-mod stone return - shapes oscB curve
    rungle = In.kr(customBus4);    // P5: Rungle ancient chaos - reshapes rune network

    // BENJOLIN CROSS-MOD: Angular rune network
    oscAMod = oscA * (0.4 + (xret * 0.6)) * (1 + (rungle * 0.3));
    oscBMod = oscB * (0.35 + (rungle * 0.65)) * (1 + (xmod * 0.25));
    xmodMod = xmod * (1 + (oscA * oscB * 0.5));
    xretMod = xret * (1 + (oscB * rungle * 0.4));
    rungleMod = rungle * (1 + (xmod * xret * 0.35));

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

    // DSP: Runic patterns with hard sync cross-mod
    
    // Sync ratio from cross-mod
    syncRatio = xmodMod.linlin(0, 1, 1.5, 4);
    
    // Voice A: Master oscillator - angular saw
    voiceA = LFSaw.ar(freq * oscAMod.linlin(0, 1, 0.5, 2), 0, 0.3);
    
    // Voice B: Slave oscillator - synced to A
    voiceB = SyncSaw.ar(
        freq * oscAMod.linlin(0, 1, 0.5, 2),  // sync freq
        freq * oscBMod.linlin(0, 1, 1, 3) * syncRatio,  // saw freq
        0.3
    );
    
    // Cross-mod: Sync ratio influenced by both voices
    voiceB = voiceB * (1 + (voiceA * xmodMod * 0.3));
    voiceA = voiceA * (1 + (voiceB * xretMod * 0.25));
    
    // Carve: Additional sync layers
    carve = SyncSaw.ar(
        freq * 2,
        freq * xmodMod.linlin(0, 1, 3, 8),
        0.15
    );
    carve = carve * rungleMod;
    
    // Stone: Angular pulse undertone
    stone = Pulse.ar(
        freq * oscBMod.linlin(0, 1, 0.5, 1),
        xretMod.linlin(0, 1, 0.2, 0.8),
        0.15
    );
    stone = stone * (1 + (LFNoise0.kr(rungleMod * 3 + 0.5) * 0.2));
    
    sig = (voiceA * 0.3) + (voiceB * 0.3) + carve + (stone * (1 - (rungleMod * 0.5)));
    
    // Angular modulation
    sig = sig * (1 + (LFPulse.kr(oscAMod * 2 + 0.5, 0, 0.5) * xretMod * 0.15));
    
    // Rune resonance
    sig = sig + (Ringz.ar(sig * 0.1, freq * [2.3, 3.7], xmodMod.linlin(0, 1, 0.02, 0.08)).sum * 0.2);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_harga_runa loaded".postln;
