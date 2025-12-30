SynthDef(\forge_wicker_hive, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var swarm, frenzy, queen, comb, trap;
    var swarmMod, frenzyMod, queenMod, combMod, trapMod;
    var carrier, modulator, buzz, hive, density;

    // Read custom params
    swarm = In.kr(customBus0);     // P1: Swarm density - scaled by queen
    frenzy = In.kr(customBus1);    // P2: Frenzy intensity - curve set by trap
    queen = In.kr(customBus2);     // P3: Queen presence - modulates swarm AND comb
    comb = In.kr(customBus3);      // P4: Comb resonance - feeds back to frenzy
    trap = In.kr(customBus4);      // P5: Trapped chaos - master reshaper

    // BUTTERFLY EFFECT: Cross-modulation network
    swarmMod = swarm * (0.3 + (queen * 0.7));
    frenzyMod = frenzy.linexp(0, 1, 0.1, 10) * (1 + (comb * trap * 2));
    queenMod = queen * (1 + (trap.squared * 0.5));
    combMod = comb * (0.5 + (swarm * frenzy * 0.5));
    trapMod = trap * (1 + (queen * comb * 0.3));

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

    // DSP: Bee swarm via ring modulation
    density = swarmMod.linexp(0, 1, 2, 40);
    
    // Carrier: base frequency with slight chaos
    carrier = SinOsc.ar(freq * [1, 1.002]) * 0.3;
    carrier = carrier + (LFNoise1.ar(frenzyMod * 20) * 0.1 * trapMod);
    
    // Modulator: buzzing frequencies influenced by queen
    modulator = SinOsc.ar(freq * queenMod.linlin(0, 1, 3, 7));
    modulator = modulator + SinOsc.ar(freq * queenMod.linlin(0, 1, 5, 11) * (1 + (trapMod * 0.2)));
    
    // Ring mod creates inharmonic bee-like tones
    buzz = carrier * modulator;
    
    // Add swarm texture - many small buzzes
    hive = Ringz.ar(
        Dust.ar(density * [1, 1.1]),
        freq * [2.3, 3.7, 5.1, 7.3],
        combMod.linlin(0, 1, 0.02, 0.2)
    ).sum * 0.15;
    
    // Blend based on trap (chaos axis)
    sig = (buzz * (1 - (trapMod * 0.3))) + (hive * trapMod);
    
    // Comb filtering for honeycomb resonance
    sig = sig + (CombL.ar(sig, 0.05, freq.reciprocal * combMod.linlin(0, 1, 1, 4), combMod * 0.3) * 0.3);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_wicker_hive loaded".postln;
