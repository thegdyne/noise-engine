SynthDef(\forge_nexus_tower, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var pwr, hrc, ego, cld, dst;
    var power, hierarchy, narcissism, cold, vastness;

    // Read custom params - power hierarchy topology
    pwr = In.kr(customBus0);       // P1: Fundamental power (bass weight)
    hrc = In.kr(customBus1);       // P2: Hierarchy steepness (partial rolloff)
    ego = In.kr(customBus2);       // P3: Self-resonance (feedback narcissism)
    cld = In.kr(customBus3);       // P4: Cold filter (ice vs warmth)
    dst = In.kr(customBus4);       // P5: Distance (vast reverberant space)

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

    // DSP: Wallace Corp monolith - power hierarchy
    
    // Power: massive fundamental
    power = SinOsc.ar(freq * [0.5, 1], 0, [0.3, 0.25] * pwr.linlin(0, 1, 0.5, 1.2)).sum;
    power = power + (LFTri.ar(freq * 0.5, 0, 0.15) * pwr);
    power = power + (Pulse.ar(freq * 0.25, 0.3, 0.1) * pwr * pwr);
    
    // Hierarchy: partials with steep rolloff
    hierarchy = Mix.fill(8, { |i|
        var partial, rolloff, drift;
        partial = i + 2;
        rolloff = (1 / (partial ** hrc.linlin(0, 1, 0.5, 2)));
        drift = LFNoise1.kr(0.1 * (i + 1)).range(0.998, 1.002);
        SinOsc.ar(freq * partial * drift, 0, rolloff * 0.15)
    });
    hierarchy = hierarchy * hrc.linlin(0, 1, 0.3, 1);
    
    // Ego: self-resonant feedback using SinOscFB
    narcissism = SinOscFB.ar(freq, ego.linexp(0, 1, 0.1, 1.5)) * 0.2;
    narcissism = narcissism * ego.linlin(0, 1, 0.2, 0.8);
    
    // Cold: ice filtering
    cold = power + hierarchy + narcissism;
    cold = RHPF.ar(cold, cld.linexp(0, 1, 80, 800), 0.5) * cld;
    cold = cold + (RLPF.ar(power + hierarchy + narcissism, cld.linexp(0, 1, 8000, 2000), 0.5) * (1 - cld));
    
    // Distance: vast reverberant space
    vastness = cold;
    vastness = vastness + (CombL.ar(vastness, 0.3, dst.linlin(0, 1, 0.08, 0.25), dst * 3) * 0.3);
    vastness = vastness + (AllpassC.ar(vastness, 0.1, dst.linlin(0, 1, 0.02, 0.08), dst * 1.5) * 0.2);
    
    sig = (cold * (1 - (dst * 0.5))) + (vastness * dst);
    
    // Monolithic presence
    sig = sig * (1 + (SinOsc.kr(pwr * 0.05 + 0.02) * 0.1));

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_nexus_tower loaded".postln;
