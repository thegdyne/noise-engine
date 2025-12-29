SynthDef(\forge_aurora_cave_gloice, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                        filterTypeBus, envEnabledBus, envSourceBus=0,
                                        clockRateBus, clockTrigBus,
                                        midiTrigBus=0, slotIndex=0,
                                        customBus0, customBus1, customBus2, customBus3, customBus4,
                                        portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var density, glow, grain, scatter, frost;
    var grainTrig, grainDur, grainPitch, grains, frostLayer;
    var buf;

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
    density = In.kr(customBus0);
    glow = In.kr(customBus1);
    grain = In.kr(customBus2);
    scatter = In.kr(customBus3);
    frost = In.kr(customBus4);

    // Grain triggering
    grainTrig = Dust.ar(density.linexp(0, 1, 5, 100));
    grainDur = grain.linexp(0, 1, 0.01, 0.15);
    
    // Pitch variation for scatter effect
    grainPitch = freq * (1 + (TRand.ar(-1, 1, grainTrig) * scatter * 0.5));

    // Granular synthesis using sinusoidal grains (no buffer needed)
    grains = Array.fill(6, { |i|
        var trig = Dust.ar(density.linexp(0, 1, 2, 40));
        var pitchVar = 1 + (TRand.ar(-1, 1, trig) * scatter * 0.3);
        var harmonic = [1, 2, 3, 4, 5, 6][i];
        var grainEnv = EnvGen.ar(
            Env.perc(0.001, grain.linexp(0, 1, 0.02, 0.2)),
            trig
        );
        SinOsc.ar(freq * harmonic * pitchVar) * grainEnv * (1 / harmonic.sqrt)
    }).sum;

    // Add higher sparkle layer
    grains = grains + Array.fill(4, { |i|
        var trig = Dust.ar(density.linexp(0, 1, 3, 60) * glow);
        var pitchVar = 1 + (TRand.ar(-0.5, 0.5, trig) * scatter);
        var sparkleFreq = freq * [5, 7, 9, 11][i] * pitchVar;
        var grainEnv = EnvGen.ar(
            Env.perc(0.0005, grain.linexp(0, 1, 0.01, 0.08)),
            trig
        );
        SinOsc.ar(sparkleFreq) * grainEnv * 0.15 * glow
    }).sum;

    // Frost texture - high frequency haze
    frostLayer = WhiteNoise.ar * frost * 0.05;
    frostLayer = BPF.ar(frostLayer, freq * 8, 0.5);
    frostLayer = frostLayer * LFNoise2.kr(2).range(0.3, 1);

    sig = (grains * 0.25) + frostLayer;
    
    // Glow saturation
    sig = (sig * (1 + glow)).tanh * (1 / (1 + (glow * 0.5)));

    sig = LeakDC.ar(sig);
    sig = ~stereoSpread.(sig, 0.5, 0.7);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_aurora_cave_gloice loaded".postln;
