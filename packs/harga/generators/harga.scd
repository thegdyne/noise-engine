SynthDef(\forge_harga_harga, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var oscA, oscB, xmod, xret, rungle;
    var oscAMod, oscBMod, xmodMod, xretMod, rungleMod;
    var voiceA, voiceB, commune, unison;

    // Read custom params - Benjolin cross-mod structure
    oscA = In.kr(customBus0);      // P1: Osc A elder tone - influenced by xret return
    oscB = In.kr(customBus1);      // P2: Osc B youth voice - scaled by rungle chaos
    xmod = In.kr(customBus2);      // P3: Cross-mod merge depth - feeds back through oscA
    xret = In.kr(customBus3);      // P4: Cross-mod echo return - shapes oscB curve
    rungle = In.kr(customBus4);    // P5: Rungle communion - reshapes voice network

    // BENJOLIN CROSS-MOD: Voices merging network
    oscAMod = oscA * (0.35 + (xret * 0.65)) * (1 + (rungle * 0.25));
    oscBMod = oscB * (0.4 + (rungle * 0.6)) * (1 + (xmod * 0.25));
    xmodMod = xmod * (1 + (oscA * oscB * 0.45));
    xretMod = xret * (1 + (oscB * rungle * 0.35));
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

    // DSP: Commune voices with cross-mod harmonics
    
    // Voice A: Elder drone - harmonic stack
    voiceA = Mix.fill(6, { |i|
        var partial, drift, gain;
        partial = i + 1;
        drift = SinOsc.kr(oscAMod * 0.2 * (i + 1), i * 0.5).range(0.998, 1.002);
        gain = (1 / partial.sqrt) * (1 - (i * 0.1 * xretMod));
        SinOsc.ar(freq * partial * drift, 0, gain.max(0))
    }) * 0.2;
    
    // Voice B: Youth response - offset harmonics
    voiceB = Mix.fill(5, { |i|
        var partial, phase, gain;
        partial = i + 1.5;  // offset partials
        phase = voiceA * xmodMod * pi * 0.5;  // modulated by A
        gain = (1 / (i + 2)) * oscBMod;
        SinOsc.ar(freq * partial * (1 + (rungleMod * 0.02)), phase, gain)
    }) * 0.25;
    
    // Cross-mod return: B shapes A's spectrum
    voiceA = voiceA * (1 + (voiceB * xretMod * 0.3));
    
    // Commune blend: voices merge
    commune = voiceA + voiceB;
    
    // Unison drift: everyone slightly different
    unison = DelayC.ar(commune, 0.05, LFNoise1.kr(rungleMod + 0.1).range(0.01, 0.04));
    unison = unison * xmodMod * 0.3;
    
    sig = commune + unison;
    
    // Communal breathing
    sig = sig * (1 + (SinOsc.kr(oscAMod * 0.1 + 0.05) * 0.15));
    
    // Rungle injection: collective unconscious
    sig = sig + (LFNoise1.ar(rungleMod * 30 + 5) * rungleMod * 0.08);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_harga_harga loaded".postln;
