SynthDef(\forge_harga_cliff, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var oscA, oscB, xmod, xret, rungle;
    var oscAMod, oscBMod, xmodMod, xretMod, rungleMod;
    var voiceA, voiceB, vertigo, fall;

    // Read custom params - Benjolin cross-mod structure
    oscA = In.kr(customBus0);      // P1: Osc A edge tone - influenced by xret return
    oscB = In.kr(customBus1);      // P2: Osc B abyss drone - scaled by rungle chaos
    xmod = In.kr(customBus2);      // P3: Cross-mod vertigo depth - feeds back through oscA
    xret = In.kr(customBus3);      // P4: Cross-mod gravity return - shapes oscB curve
    rungle = In.kr(customBus4);    // P5: Rungle falling chaos - reshapes descent network

    // BENJOLIN CROSS-MOD: Vertigo feedback network
    oscAMod = oscA * (0.3 + (xret * 0.7)) * (1 + (rungle * 0.4));
    oscBMod = oscB * (0.35 + (rungle * 0.65)) * (1 + (xmod * 0.3));
    xmodMod = xmod * (1 + (oscA * oscB * 0.6));
    xretMod = xret * (1 + (oscB * rungle * 0.5));
    rungleMod = rungle * (1 + (xmod * xret * 0.45));

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

    // DSP: Ättestupa vertigo with chaos cross-mod
    
    // Falling rate from rungle
    fall = LFNoise2.kr(rungleMod * 3 + 0.2).range(0.5, 4);
    
    // Voice A: Edge chaos - Crackle-based instability
    voiceA = Crackle.ar(oscAMod.linlin(0, 1, 1.5, 1.95)) * 0.3;
    voiceA = voiceA + (LFNoise0.ar(freq * oscAMod.linlin(0, 1, 0.5, 2)) * 0.2);
    voiceA = RLPF.ar(voiceA, freq * xmodMod.linlin(0, 1, 1, 8), 0.3);
    
    // Voice B: Abyss - deep unstable tones
    voiceB = SinOsc.ar(
        freq * oscBMod.linlin(0, 1, 0.25, 1) * (1 + (voiceA * xmodMod * 0.5)),
        0,
        0.3
    );
    voiceB = voiceB + (LFTri.ar(freq * 0.5 * (1 + (rungleMod * 0.2))) * 0.15);
    
    // Cross-mod: A and B destabilize each other
    voiceA = voiceA * (1 + (voiceB * xretMod * 0.6));
    voiceB = voiceB * (1 + (voiceA * xmodMod * 0.4));
    
    // Vertigo: spinning disorientation
    vertigo = SinOsc.ar(freq * [1, 1.01, 0.99], LFSaw.kr(fall).range(0, 2pi), 0.15).sum;
    vertigo = vertigo * (1 + (SinOsc.kr(fall * 2) * xretMod * 0.3));
    
    sig = (voiceA * 0.35) + (voiceB * 0.35) + (vertigo * rungleMod);
    
    // Falling pitch drift
    sig = sig + (PitchShift.ar(sig, 0.1, LFNoise1.kr(fall).range(0.98, 1.02)) * rungleMod * 0.2);
    
    // Abyss reverb
    sig = sig + (CombL.ar(sig, 0.3, xretMod.linlin(0, 1, 0.1, 0.25), rungleMod * 1.5) * 0.2);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_harga_cliff loaded".postln;
