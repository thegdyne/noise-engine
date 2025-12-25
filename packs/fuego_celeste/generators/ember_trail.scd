SynthDef(\forge_fuego_celeste_ember_trail, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                             filterTypeBus, envEnabledBus, envSourceBus=0,
                                             clockRateBus, clockTrigBus,
                                             midiTrigBus=0, slotIndex=0,
                                             customBus0, customBus1, customBus2, customBus3, customBus4,
                                             portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var sparks, flow, glow, cool, scatter;
    var sparkDust, flowLFO, glowRing, coolDecay, emberPing;

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

    // Theme parameters
    sparks = In.kr(customBus0);     // density
    flow = In.kr(customBus1);       // downward rate
    glow = In.kr(customBus2);       // brightness
    cool = In.kr(customBus3);       // fade rate
    scatter = In.kr(customBus4);    // spread

    // Spark impulses - random dust
    sparkDust = Dust.ar(sparks.linexp(0, 1, 5, 100));

    // Downward flow - falling pitch modulation
    flowLFO = LFSaw.kr(flow.linexp(0, 1, 0.2, 3), 1).range(1.5, 0.5);

    // Cool decay time - how fast embers fade
    coolDecay = cool.linexp(0, 1, 0.5, 0.05);

    // Glowing resonance - bright ringing per spark
    glowRing = Ringz.ar(sparkDust, freq * flowLFO * [1, 1.5, 2], coolDecay);
    glowRing = Mix(glowRing) * glow;

    // Add crackle layer
    emberPing = sparkDust * Crackle.ar(1.8) * 0.3;
    emberPing = HPF.ar(emberPing, 2000);

    // Higher pitched sparkles
    emberPing = emberPing + (Ringz.ar(sparkDust * 0.5, freq * flowLFO * 4, coolDecay * 0.5) * glow * 0.3);

    // Mix
    sig = (glowRing * 0.5) + emberPing;

    // Scatter - stereo randomization
    sig = Pan2.ar(sig, TRand.kr(-1, 1, sparkDust) * scatter);

    // Standard post-chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;
"  * forge_fuego_celeste_ember_trail loaded".postln;
