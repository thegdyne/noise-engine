// Micro Shimmer - Light dancing on countless tiny droplets
// Granular texture with scattered pitched sparkles

SynthDef(\forge_dew_sphere_micro_shimmer, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
    filterTypeBus, envEnabledBus, envSourceBus=0,
    clockRateBus, clockTrigBus,
    midiTrigBus=0, slotIndex=0,
    customBus0, customBus1, customBus2, customBus3, customBus4,
    portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var spark, amount, scatter, strobe, width;
    var triggers, sparkles, scatterFreqs;
    var sparkL, sparkR, strobeEnv;

    // Standard bus reads
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
    spark = In.kr(customBus0);      // Sparkle density
    amount = In.kr(customBus1);     // Intensity
    scatter = In.kr(customBus2);    // Pitch scatter
    strobe = In.kr(customBus3);     // Flicker rate
    width = In.kr(customBus4);      // Stereo width

    // Strobe trigger rate
    triggers = Dust.ar(spark.linexp(0, 1, 5, 80));

    // Scattered frequencies around base pitch
    scatterFreqs = freq * [1, 1.5, 2, 2.5, 3, 4] * LFNoise1.kr(0.5!6).range(1 - (scatter * 0.2), 1 + (scatter * 0.2));

    // Multiple tiny resonant sparkles
    sparkles = Ringz.ar(
        triggers,
        scatterFreqs,
        strobe.linexp(0, 1, 0.01, 0.15)
    ).sum * 0.15;

    // Strobe amplitude modulation
    strobeEnv = LFNoise2.kr(strobe.linexp(0, 1, 2, 20)).range(0.3, 1);
    sparkles = sparkles * strobeEnv;

    // High-frequency glitter layer
    sparkles = sparkles + (
        Ringz.ar(
            Dust.ar(spark.linexp(0, 1, 10, 150)),
            freq * [5, 6, 7, 8] * LFNoise1.kr(1!4).range(0.9, 1.1),
            0.02
        ).sum * scatter * 0.1
    );

    // Stereo spread - different sparkles L/R
    sparkL = sparkles + (
        Ringz.ar(Dust.ar(spark * 20), freq * 1.01, 0.05) * width * 0.2
    );
    sparkR = sparkles + (
        Ringz.ar(Dust.ar(spark * 20), freq * 0.99, 0.05) * width * 0.2
    );

    sig = [sparkL, sparkR] * amount;

    // Gentle lowpass to tame harshness
    sig = LPF.ar(sig, 12000);

    // Amount scaling
    sig = sig * 0.6;

    // Output chain (already stereo)
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_dew_sphere_micro_shimmer loaded".postln;
