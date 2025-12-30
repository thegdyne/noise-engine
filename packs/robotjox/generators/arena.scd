SynthDef(\forge_robotjox_arena, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                    filterTypeBus, envEnabledBus, envSourceBus=0,
                                    clockRateBus, clockTrigBus,
                                    midiTrigBus=0, slotIndex=0,
                                    customBus0, customBus1, customBus2, customBus3, customBus4,
                                    portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, envSource, clockRate, portamento;
    var windAmt, crowd, dust, vast, tension;
    var windNoise, crowdRoar, dustStorm, space, tensionMod;

    // Theme params
    windAmt = In.kr(customBus0);
    crowd = In.kr(customBus1);
    dust = In.kr(customBus2);
    vast = In.kr(customBus3);
    tension = In.kr(customBus4);

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

    // Tension modulation - slow undulation
    tensionMod = LFNoise2.kr(0.2 + (tension * 0.5)).range(0.7, 1.0);

    // Wasteland wind
    windNoise = PinkNoise.ar(0.4) + BrownNoise.ar(0.3);
    windNoise = BPF.ar(windNoise, freq * LFNoise2.kr(0.3).range(0.5, 2), 0.5) * 2;
    windNoise = windNoise * LFNoise2.kr(0.4 + (windAmt * 0.5)).range(0.4, 1.0);
    windNoise = windNoise * (0.4 + (windAmt * 0.6));

    // Distant crowd roar
    crowdRoar = LPF.ar(BrownNoise.ar(0.5), 200 + (crowd * 300));
    crowdRoar = crowdRoar * LFNoise2.kr(0.3).range(0.5, 1.0);
    crowdRoar = crowdRoar * (0.3 + (crowd * 0.7));

    // Dust storm high frequencies
    dustStorm = HPF.ar(WhiteNoise.ar(0.25), 2000 + (dust * 3000));
    dustStorm = dustStorm * LFNoise2.kr(2 + (dust * 5)).range(0.3, 1.0);
    dustStorm = dustStorm * dust;

    sig = windNoise + crowdRoar + dustStorm;

    // Apply tension
    sig = sig * tensionMod;

    // Arena vastness - allpass reverb
    space = sig;
    space = AllpassC.ar(space, 0.3, vast.linlin(0, 1, 0.05, 0.2), vast * 3);
    space = AllpassC.ar(space, 0.3, vast.linlin(0, 1, 0.08, 0.25), vast * 2.5);
    space = AllpassC.ar(space, 0.3, vast.linlin(0, 1, 0.03, 0.15), vast * 2);

    sig = (sig * (1 - (vast * 0.4))) + (space * vast * 0.6);

    // Pitched wind resonance
    sig = sig + BPF.ar(PinkNoise.ar(0.2), freq, 0.3) * 2;

    // Continuous bed
    sig = sig + LPF.ar(BrownNoise.ar(0.12), 250);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, 0.2, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_robotjox_arena loaded".postln;
