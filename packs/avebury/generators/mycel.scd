SynthDef(\forge_avebury_mycel, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                   filterTypeBus, envEnabledBus, envSourceBus=0,
                                   clockRateBus, clockTrigBus,
                                   midiTrigBus=0, slotIndex=0,
                                   customBus0, customBus1, customBus2, customBus3, customBus4,
                                   portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, envSource, clockRate, portamento;
    var network, spread, signalParam, growth, soil;
    var grains, grainRate, grainFreq, trig1, trig2, trig3, trig4;
    var soilNoise, growthMod, signalMod;

    // Theme params
    network = In.kr(customBus0);
    spread = In.kr(customBus1);
    signalParam = In.kr(customBus2);
    growth = In.kr(customBus3);
    soil = In.kr(customBus4);

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

    // Growth modulation - slow evolution
    growthMod = LFNoise2.kr(growth.linexp(0, 1, 0.05, 0.3)).range(0.7, 1.0);

    // Signal modulation - chemical pulses
    signalMod = LFPulse.kr(signalParam.linexp(0, 1, 0.1, 2), 0, 0.3).lag(0.1);
    signalMod = signalMod * LFNoise2.kr(0.5).range(0.5, 1.0);

    // Grain rate based on network density
    grainRate = network.linexp(0, 1, 5, 50);

    // Multiple grain streams at different pitches (simulating granular cloud)
    trig1 = Dust.ar(grainRate);
    trig2 = Dust.ar(grainRate * 0.8);
    trig3 = Dust.ar(grainRate * 1.2);
    trig4 = Dust.ar(grainRate * 0.5);

    // Grains as short resonances with pitch spread
    grainFreq = freq * LFNoise0.kr(10).range(1 - (spread * 0.2), 1 + (spread * 0.2));
    grains = Ringz.ar(trig1, grainFreq, 0.05 + (growth * 0.1), 0.2);
    grains = grains + Ringz.ar(trig2, freq * (1 + (spread * 0.15)), 0.04 + (growth * 0.08), 0.18);
    grains = grains + Ringz.ar(trig3, freq * (1 - (spread * 0.15)), 0.06 + (growth * 0.12), 0.15);
    grains = grains + Ringz.ar(trig4, freq * 0.5, 0.1 + (growth * 0.15), 0.25);

    // Apply signal modulation
    grains = grains * (0.5 + (signalMod * 0.5));
    grains = grains * growthMod;

    sig = grains * 0.5;

    // Soil texture - continuous noise bed
    soilNoise = LPF.ar(BrownNoise.ar(0.2), 300 + (freq * 0.5));
    soilNoise = soilNoise + BPF.ar(PinkNoise.ar(0.15), freq, 0.4) * 2;
    soilNoise = soilNoise * LFNoise2.kr(0.3).range(0.6, 1.0);

    sig = sig + (soilNoise * soil);

    // Network hum - subtle pitched drone
    sig = sig + SinOsc.ar(freq * 0.25, 0, 0.1 * network);
    sig = sig + SinOsc.ar(freq, 0, 0.05);

    // Continuous bed
    sig = sig + LPF.ar(PinkNoise.ar(0.08), 400);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, 0.2, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_avebury_mycel loaded".postln;
