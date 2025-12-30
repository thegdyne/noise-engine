SynthDef(\forge_nexus_baseline, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var pls, cel, int, drd, brk;
    var pulse, cells, interlink, dread, breakdown, gridTrig, cellLayers;

    // Read custom params - baseline test topology
    pls = In.kr(customBus0);       // P1: Pulse intensity (rhythmic drive)
    cel = In.kr(customBus1);       // P2: Cells interlinked (layer density)
    int = In.kr(customBus2);       // P3: Interlink strength (cross-mod between cells)
    drd = In.kr(customBus3);       // P4: Dread buildup (tension accumulation)
    brk = In.kr(customBus4);       // P5: Breakdown (grid dissolution)

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

    // DSP: Baseline VK test - within cells interlinked
    
    // Grid trigger: locked pulse (disrupted by breakdown)
    gridTrig = Impulse.ar(pls.linexp(0, 1, 1, 8) * (1 - (brk * 0.5)));
    gridTrig = gridTrig + (Dust.ar(brk.linexp(0, 1, 0.1, 20)) * brk);
    
    // Pulse: base rhythmic membrane
    pulse = Ringz.ar(gridTrig, freq * [1, 1.5, 2], pls.linlin(0, 1, 0.05, 0.2)).sum * 0.3;
    pulse = pulse + (SinOsc.ar(freq, 0, 0.2) * Decay.ar(gridTrig, pls.linlin(0, 1, 0.1, 0.3)));
    
    // Cells: layered membrane grid
    cellLayers = Mix.fill(4, { |i|
        var cellFreq, cellPhase, cellAmp;
        cellFreq = freq * (i + 1) * cel.linlin(0, 1, 1, 1.2);
        cellPhase = pulse * int * pi * (i + 1);  // interlinked phase
        cellAmp = cel / (i + 2);
        Ringz.ar(gridTrig, cellFreq, 0.1, cellAmp) + (SinOsc.ar(cellFreq, cellPhase, cellAmp * 0.3))
    });
    
    // Interlink: cells modulate each other
    interlink = cellLayers * (1 + (pulse * int * 0.5));
    interlink = interlink + (cellLayers * SinOsc.ar(freq * 0.5, 0, int * 0.3));
    
    // Dread: tension accumulation filter sweep
    dread = pulse + interlink;
    dread = RLPF.ar(dread, drd.linexp(0, 1, 500, 4000), 0.3 + (drd * 0.4));
    dread = dread * (1 + (SinOsc.kr(drd * 0.2 + 0.05) * drd * 0.3));
    dread = dread + (BrownNoise.ar(drd * 0.08));
    
    // Breakdown: grid dissolution
    breakdown = dread;
    breakdown = breakdown * (1 - (brk * 0.3));
    breakdown = breakdown + (
        Ringz.ar(Dust.ar(brk.linexp(0, 1, 1, 50) * [1, 1.1]), 
        freq * [2.3, 3.7, 5.1], 
        brk.linlin(0, 1, 0.02, 0.1)).sum * brk * 0.3
    );
    breakdown = breakdown + (LFNoise0.ar(brk * 100 + 10) * brk * 0.1);
    
    sig = breakdown;
    
    // Continuous drone bed for stability
    sig = sig + (SinOsc.ar(freq * [1, 0.5], 0, 0.1 * (1 - (brk * 0.5))).sum);
    
    // Within cells: subtle stereo phase
    sig = [sig, DelayC.ar(sig, 0.01, cel * 0.005)];

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_nexus_baseline loaded".postln;
