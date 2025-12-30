SynthDef(\forge_harga_tempel, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var oscA, oscB, xmod, xret, rungle;
    var oscAMod, oscBMod, xmodMod, xretMod, rungleMod;
    var voiceA, voiceB, flame, ash, foldAmt;

    // Read custom params - Benjolin cross-mod structure
    oscA = In.kr(customBus0);      // P1: Osc A flame core - influenced by xret return
    oscB = In.kr(customBus1);      // P2: Osc B ember glow - scaled by rungle chaos
    xmod = In.kr(customBus2);      // P3: Cross-mod burn depth - feeds back through oscA
    xret = In.kr(customBus3);      // P4: Cross-mod smoke return - shapes oscB curve
    rungle = In.kr(customBus4);    // P5: Rungle sacrifice chaos - reshapes temple network

    // BENJOLIN CROSS-MOD: Burning temple network
    oscAMod = oscA * (0.35 + (xret * 0.65)) * (1 + (rungle * 0.35));
    oscBMod = oscB * (0.4 + (rungle * 0.6)) * (1 + (xmod * 0.3));
    xmodMod = xmod * (1 + (oscA * oscB * 0.55));
    xretMod = xret * (1 + (oscB * rungle * 0.45));
    rungleMod = rungle * (1 + (xmod * xret * 0.4));

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

    // DSP: Yellow temple burning with wavefold cross-mod
    
    // Fold amount from cross-mod
    foldAmt = xmodMod.linlin(0, 1, 1, 4);
    
    // Voice A: Flame core - wavefolded saw
    voiceA = LFSaw.ar(freq * oscAMod.linlin(0, 1, 0.5, 2), 0, 0.8);
    voiceA = (voiceA * foldAmt).fold2(1) * 0.4;
    voiceA = voiceA + ((voiceA * xretMod * 2).tanh * 0.2);
    
    // Voice B: Ember glow - softer fold
    voiceB = SinOsc.ar(freq * oscBMod.linlin(0, 1, 1, 3), 0, 0.6);
    voiceB = voiceB + (LFTri.ar(freq * oscBMod.linlin(0, 1, 0.5, 1.5), 0, 0.3));
    voiceB = (voiceB * (1 + (rungleMod * 2))).fold2(1) * 0.35;
    
    // Cross-mod: Flames feed each other
    voiceA = voiceA * (1 + (voiceB * xmodMod * 0.4));
    voiceB = voiceB + (voiceA * xretMod * 0.3);
    
    // Additional fold cascade
    voiceA = (voiceA * (1 + xretMod)).fold2(1);
    
    // Flame: Crackling destruction
    flame = Crackle.ar(rungleMod.linlin(0, 1, 1.3, 1.8)) * 0.15;
    flame = RLPF.ar(flame, freq * xmodMod.linlin(0, 1, 2, 8), 0.4);
    
    // Ash: What remains
    ash = PinkNoise.ar(0.1) * rungleMod;
    ash = RLPF.ar(ash, freq * xretMod.linlin(0, 1, 0.5, 2), 0.5);
    
    sig = (voiceA * 0.35) + (voiceB * 0.3) + flame + ash;
    
    // Burning intensity modulation
    sig = sig * (1 + (LFNoise2.kr(rungleMod * 3 + 0.5) * xmodMod * 0.2));
    
    // Heat shimmer
    sig = sig + (DelayC.ar(sig, 0.03, SinOsc.kr(oscAMod * 2).range(0.01, 0.025)) * rungleMod * 0.15);
    
    // Temple resonance
    sig = sig + (CombL.ar(sig * 0.3, 0.2, xretMod.linlin(0, 1, 0.05, 0.15), rungleMod * 0.8) * 0.2);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_harga_tempel loaded".postln;
