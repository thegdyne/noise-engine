SynthDef(\forge_nexus_rain, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var drp, srf, neo, mir, fog;
    var drops, surface, neon, mirror, atmosphere;

    // Read custom params - rain parallel topology
    drp = In.kr(customBus0);       // P1: Drop density (excitation rate)
    srf = In.kr(customBus1);       // P2: Surface tension (resonance character)
    neo = In.kr(customBus2);       // P3: Neon color (harmonic tint)
    mir = In.kr(customBus3);       // P4: Mirror pooling (reflections/delay)
    fog = In.kr(customBus4);       // P5: Atmospheric diffusion

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

    // DSP: Eternal rain with neon reflections
    
    // Drops: density-controlled impulse rain
    drops = Dust.ar(drp.linexp(0, 1, 5, 200) * [1, 1.1, 0.9]);
    drops = Ringz.ar(drops, freq * [2.3, 4.7, 7.1], srf.linlin(0, 1, 0.02, 0.15)).sum * 0.2;
    drops = drops * (1 + (LFNoise1.kr(drp * 3) * 0.3));
    
    // Surface: water tension resonance
    surface = BrownNoise.ar(0.15) + (PinkNoise.ar(0.1) * srf);
    surface = Resonz.ar(surface, freq * srf.linlin(0, 1, 1, 4), 0.1) * 4;
    surface = surface + (SinOsc.ar(freq * 0.5, 0, 0.1) * srf);
    
    // Neon: harmonic color from city lights
    neon = Mix.fill(4, { |i|
        var ratio, brightness;
        ratio = (i + 2) * neo.linlin(0, 1, 1, 1.5);
        brightness = 0.1 / (i + 1);
        SinOsc.ar(freq * ratio, 0, brightness)
    });
    neon = neon * neo.linlin(0, 1, 0.2, 1);
    neon = neon * (1 + (LFTri.kr(neo * 2 + 0.5) * 0.2));
    
    // Mirror: pooling reflections
    mirror = drops + surface;
    mirror = CombL.ar(mirror, 0.3, mir.linlin(0, 1, 0.05, 0.2), mir * 2);
    mirror = mirror * mir * 0.4;
    
    // Atmosphere: fog diffusion
    atmosphere = drops + surface + neon;
    atmosphere = LPF.ar(atmosphere, fog.linexp(0, 1, 8000, 800));
    atmosphere = atmosphere + (PinkNoise.ar(fog * 0.1));
    
    sig = (drops * 0.4) + (surface * 0.3) + (neon * 0.4) + mirror + (atmosphere * fog * 0.3);
    
    // Eternal rain stereo spread
    sig = [sig, DelayC.ar(sig, 0.05, LFNoise1.kr(0.3).range(0.01, 0.04))];

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_nexus_rain loaded".postln;
