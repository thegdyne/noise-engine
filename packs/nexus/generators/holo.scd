SynthDef(\forge_nexus_holo, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var sol, flk, prj, ght, syn;
    var solid, flicker, beam, ghost, carrier, modPhase;

    // Read custom params - holographic phase interference
    sol = In.kr(customBus0);       // P1: Solidity (presence stability)
    flk = In.kr(customBus1);       // P2: Flicker rate (instability frequency)
    prj = In.kr(customBus2);       // P3: Projection beam (stereo/distance)
    ght = In.kr(customBus3);       // P4: Ghost trails (temporal smear)
    syn = In.kr(customBus4);       // P5: Sync lock (chaos to grid)

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

    // DSP: Holographic phase modulation with flicker
    
    // Flicker: instability generator (syncs to grid at high syn)
    flicker = LFNoise0.kr(flk.linexp(0, 1, 2, 50));
    flicker = (flicker * (1 - syn)) + (LFPulse.kr(flk.linexp(0, 1, 2, 20), 0, 0.5) * syn);
    flicker = flicker.range(0.3, 1);
    
    // Phase modulator - audio rate PM
    modPhase = SinOsc.ar(freq * sol.linlin(0, 1, 2, 6));
    modPhase = modPhase + (LFNoise2.ar(flk.linexp(0, 1, 100, 2000)) * (1 - sol) * 0.5);
    
    // Solid presence: main carrier with phase mod
    solid = SinOsc.ar(freq * [1, 1.002], modPhase * sol.linlin(0, 1, 0.5, 3) * pi, 0.3);
    solid = solid + SinOsc.ar(freq * 2, modPhase * pi * 0.5, 0.15 * sol);
    solid = solid * flicker;
    
    // Beam: projection harmonics with stereo spread
    beam = Mix.fill(3, { |i|
        var beamFreq, pan;
        beamFreq = freq * (i + 1) * prj.linlin(0, 1, 1, 1.5);
        pan = SinOsc.kr(prj * (i + 1) * 0.3, i).range(0.3, 0.7);
        Pan2.ar(SinOsc.ar(beamFreq, modPhase * pi, 0.08 / (i + 1)), pan * 2 - 1)
    });
    beam = beam * prj.linlin(0, 1, 0.3, 1);
    
    // Ghost: temporal smear trails
    ghost = solid + beam;
    ghost = CombL.ar(ghost, 0.2, ght.linlin(0, 1, 0.02, 0.15), ght * 1.5);
    ghost = ghost * ght * 0.4;
    
    sig = solid + beam + ghost;
    
    // Holographic shimmer
    sig = sig * (1 + (SinOsc.kr(flk * 3 + 1) * (1 - syn) * 0.15));
    
    // Sync stabilization at high values
    sig = (sig * (1 - (syn * 0.3))) + (LPF.ar(sig, 2000) * syn * 0.3);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_nexus_holo loaded".postln;
