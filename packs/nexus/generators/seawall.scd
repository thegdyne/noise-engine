SynthDef(\forge_nexus_seawall, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var mas, prs, crk, slt, tde;
    var mass, pressure, cracks, salt, tide, subFreq, foldAmt;

    // Read custom params - seawall mass topology
    mas = In.kr(customBus0);       // P1: Mass (subharmonic weight)
    prs = In.kr(customBus1);       // P2: Pressure (compression density)
    crk = In.kr(customBus2);       // P3: Cracks (stress fracture noise)
    slt = In.kr(customBus3);       // P4: Salt corrosion (textural grit)
    tde = In.kr(customBus4);       // P5: Tide cycle (slow macro modulation)

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

    // DSP: Massive seawall infrastructure
    
    // Tide: slow macro modulation cycle
    tide = SinOsc.kr(tde.linexp(0, 1, 0.02, 0.2)).range(0.7, 1);
    
    // Subharmonic frequency
    subFreq = freq * mas.linlin(0, 1, 0.5, 0.25);
    
    // Mass: heavy subharmonic weight with wavefold
    mass = LFSaw.ar(subFreq * [1, 1.003], 0, 0.6);
    foldAmt = prs.linlin(0, 1, 1, 3);
    mass = (mass * foldAmt).fold2(1) * 0.4;
    mass = mass + (SinOsc.ar(subFreq * 2, 0, 0.2) * mas);
    mass = mass + (LFTri.ar(subFreq * 0.5, 0, 0.15) * mas * mas);
    mass = mass * tide;
    
    // Pressure: compression density wavefold cascade
    pressure = mass;
    pressure = (pressure * (1 + prs)).fold2(1);
    pressure = (pressure * (1 + (prs * 0.5))).tanh;
    pressure = RLPF.ar(pressure, freq * prs.linlin(0, 1, 1, 4), 0.4);
    
    // Cracks: stress fracture noise
    cracks = Dust.ar(crk.linexp(0, 1, 0.5, 20) * [1, 1.1]);
    cracks = Ringz.ar(cracks, freq * [1.7, 2.9, 4.3], crk.linlin(0, 1, 0.02, 0.1)).sum * 0.2;
    cracks = cracks + (Crackle.ar(crk.linlin(0, 1, 1.2, 1.7)) * crk * 0.1);
    cracks = cracks * tide;
    
    // Salt: corrosion grit texture
    salt = GrayNoise.ar(0.15) + (PinkNoise.ar(0.1) * slt);
    salt = BPF.ar(salt, freq * slt.linlin(0, 1, 2, 8), 0.3) * 3;
    salt = salt + (WhiteNoise.ar(slt * 0.05));
    salt = salt * slt.linlin(0, 1, 0.2, 0.6);
    
    sig = (mass * 0.4) + (pressure * 0.3) + cracks + salt;
    
    // Tide breathing
    sig = sig * (1 + (SinOsc.kr(tde * 0.1 + 0.02) * tde * 0.15));
    
    // Massive infrastructure reverb
    sig = sig + (CombL.ar(sig, 0.3, tde.linlin(0, 1, 0.1, 0.25), tde * 2) * 0.2);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_nexus_seawall loaded".postln;
