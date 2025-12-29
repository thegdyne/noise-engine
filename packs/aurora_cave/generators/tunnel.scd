SynthDef(\forge_aurora_cave_tunnel, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                        filterTypeBus, envEnabledBus, envSourceBus=0,
                                        clockRateBus, clockTrigBus,
                                        midiTrigBus=0, slotIndex=0,
                                        customBus0, customBus1, customBus2, customBus3, customBus4,
                                        portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var wind, length, mouth, howl, cold;
    var breath, tube, hiss, modFreq;

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
    amp = In.kr(~params[\amplitude]);

    // Theme params
    wind = In.kr(customBus0);
    length = In.kr(customBus1);
    mouth = In.kr(customBus2);
    howl = In.kr(customBus3);
    cold = In.kr(customBus4);

    // Wind breath source - turbulent noise
    breath = LFNoise1.ar(wind.linexp(0, 1, 20, 200)) * wind;
    breath = breath + (LFNoise2.ar(wind.linexp(0, 1, 50, 400)) * wind * 0.5);
    breath = breath * LFNoise2.kr(wind.linexp(0, 1, 0.2, 2)).range(0.3, 1);

    // Tube resonance via waveguide
    tube = CombL.ar(
        breath, 
        0.1, 
        (freq * length.linlin(0, 1, 0.5, 2)).reciprocal, 
        howl.linlin(0, 1, 0.5, 3)
    );
    
    // Add harmonics based on mouth opening
    tube = tube + CombL.ar(
        breath * mouth, 
        0.05, 
        (freq * 2 * length.linlin(0, 1, 0.5, 2)).reciprocal, 
        howl.linlin(0, 1, 0.3, 2)
    ) * mouth;
    
    tube = tube + CombL.ar(
        breath * mouth * 0.5, 
        0.033, 
        (freq * 3 * length.linlin(0, 1, 0.5, 2)).reciprocal, 
        howl.linlin(0, 1, 0.2, 1.5)
    ) * mouth * 0.7;

    // Howling modulation
    modFreq = SinOsc.kr(howl.linexp(0, 1, 0.1, 0.8)).range(0.97, 1.03);
    tube = DelayC.ar(tube, 0.02, (freq * modFreq).reciprocal.clip(0.0001, 0.02) * howl * 0.5);

    // Cold air hiss
    hiss = WhiteNoise.ar * cold * 0.15;
    hiss = HPF.ar(hiss, cold.linexp(0, 1, 2000, 6000));
    hiss = hiss * LFNoise2.kr(1).range(0.5, 1);

    // Mix
    sig = (tube * 0.4) + hiss;
    
    // Damping based on length (longer = darker)
    sig = LPF.ar(sig, length.linexp(0, 1, 4000, 1500));

    sig = LeakDC.ar(sig);
    sig = ~stereoSpread.(sig, 0.4, 0.6);
    sig = sig * 4;
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_aurora_cave_tunnel loaded".postln;
