SynthDef(\forge_harga_krona, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var oscA, oscB, xmod, xret, rungle;
    var oscAMod, oscBMod, xmodMod, xretMod, rungleMod;
    var voiceA, voiceB, weave, crown;

    // Read custom params - Benjolin cross-mod structure
    oscA = In.kr(customBus0);      // P1: Osc A flower tone - influenced by xret return
    oscB = In.kr(customBus1);      // P2: Osc B stem resonance - scaled by rungle chaos
    xmod = In.kr(customBus2);      // P3: Cross-mod interlock depth - feeds back through oscA
    xret = In.kr(customBus3);      // P4: Cross-mod petal return - shapes oscB curve
    rungle = In.kr(customBus4);    // P5: Rungle growth chaos - reshapes crown network

    // BENJOLIN CROSS-MOD: Interlocking flower network
    oscAMod = oscA * (0.4 + (xret * 0.6)) * (1 + (rungle * 0.2));
    oscBMod = oscB * (0.35 + (rungle * 0.65)) * (1 + (xmod * 0.2));
    xmodMod = xmod * (1 + (oscA * oscB * 0.4));
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

    // DSP: Flower crown with ring mod interlocking
    
    // Voice A: Flower bell tones
    voiceA = SinOsc.ar(freq * oscAMod.linlin(0, 1, 1, 3), 0, 0.3);
    voiceA = voiceA + (SinOsc.ar(freq * oscAMod.linlin(0, 1, 2, 5), 0, 0.15));
    voiceA = voiceA * (1 + (SinOsc.kr(xretMod * 2) * 0.2));
    
    // Voice B: Stem undertone
    voiceB = LFTri.ar(freq * oscBMod.linlin(0, 1, 0.5, 1.5), 0, 0.25);
    voiceB = voiceB + (Pulse.ar(freq * oscBMod.linlin(0, 1, 1, 2), 0.3, 0.1));
    
    // Ring modulation cross-mod: flowers interlock
    weave = voiceA * voiceB * xmodMod.linlin(0, 1, 0.5, 2);
    
    // Return path: ring mod feeds back into voices
    voiceA = voiceA + (weave * xretMod * 0.3);
    voiceB = voiceB * (1 + (weave * xmodMod * 0.2));
    
    // Crown assembly
    crown = (voiceA * 0.35) + (voiceB * 0.25) + (weave * 0.3);
    
    // Delicate shimmer
    crown = crown + (Ringz.ar(
        Dust.ar(rungleMod.linexp(0, 1, 1, 10) * [1, 1.1]),
        freq * [3, 5, 7],
        xretMod.linlin(0, 1, 0.05, 0.15)
    ).sum * 0.1);
    
    sig = crown;
    
    // Growth modulation
    sig = sig * (1 + (LFNoise1.kr(rungleMod * 0.5 + 0.1) * 0.1));
    
    // Stereo weave
    sig = [sig, DelayC.ar(sig, 0.02, SinOsc.kr(oscAMod * 0.3).range(0.005, 0.015))];

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_harga_krona loaded".postln;
