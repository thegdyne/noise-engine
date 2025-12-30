SynthDef(\forge_harga_bloom, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var oscA, oscB, xmod, xret, rungle;
    var oscAMod, oscBMod, xmodMod, xretMod, rungleMod;
    var voiceA, voiceB, breathRate, petalPhase;

    // Read custom params - Benjolin cross-mod structure
    oscA = In.kr(customBus0);      // P1: Osc A petal unfurl - influenced by xret return
    oscB = In.kr(customBus1);      // P2: Osc B pollen drift - scaled by rungle chaos
    xmod = In.kr(customBus2);      // P3: Cross-mod A→B depth - feeds back through oscA
    xret = In.kr(customBus3);      // P4: Cross-mod B→A return - shapes oscB curve
    rungle = In.kr(customBus4);    // P5: Rungle chaos - reshapes entire bloom network

    // BENJOLIN CROSS-MOD: Mutual influence network
    oscAMod = oscA * (0.4 + (xret * 0.6)) * (1 + (rungle * 0.3));
    oscBMod = oscB * (0.3 + (rungle * 0.7)) * (1 + (xmod * 0.2));
    xmodMod = xmod * (1 + (oscA * oscB * 0.5));
    xretMod = xret * (1 + (oscB * rungle * 0.4));
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

    // DSP: Twin oscillator bloom with cross-modulation
    
    // Breathing rate from rungle chaos
    breathRate = LFNoise1.kr(rungleMod * 2 + 0.1).range(0.3, 2);
    
    // Oscillator A: Petal unfurl - feedback FM
    voiceA = SinOscFB.ar(
        freq * oscAMod.linlin(0, 1, 0.5, 2),
        xmodMod.linlin(0, 1, 0.1, 1.2)  // feedback from cross-mod depth
    );
    
    // Petal phase modulation from voice B feedback
    petalPhase = LFTri.kr(breathRate * xretMod.linlin(0, 1, 0.5, 3));
    voiceA = voiceA * (0.5 + (petalPhase * 0.3));
    
    // Oscillator B: Pollen drift - modulated by voice A
    voiceB = SinOsc.ar(
        freq * oscBMod.linlin(0, 1, 1, 4) * (1 + (voiceA * xmodMod * 0.3)),
        voiceA * xmodMod * pi  // phase mod from A
    );
    
    // Return path: B modulates A's amplitude
    voiceA = voiceA * (1 + (voiceB * xretMod * 0.4));
    
    // Bloom harmonics
    voiceA = voiceA + (SinOsc.ar(freq * [2.01, 3.02], 0, 0.1 * oscAMod).sum);
    voiceB = voiceB + (SinOsc.ar(freq * [1.5, 2.5], 0, 0.08 * oscBMod).sum);
    
    // Rungle injection: chaotic modulation
    sig = (voiceA * 0.4) + (voiceB * 0.3);
    sig = sig * (1 + (LFNoise2.ar(rungleMod * 50 + 1) * rungleMod * 0.3));
    
    // Stereo bloom
    sig = sig + (DelayC.ar(sig, 0.03, SinOsc.kr(breathRate).range(0.01, 0.025)) * 0.2);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_harga_bloom loaded".postln;
