// Storm Cloud - Brooding atmospheric texture
// Granular noise with slow evolution and occasional lightning

SynthDef(\forge_drangarnir_storm_cloud, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                           filterTypeBus, envEnabledBus, envSourceBus=0,
                                           clockRateBus, clockTrigBus,
                                           midiTrigBus=0, slotIndex=0,
                                           customBus0, customBus1, customBus2, customBus3, customBus4,
                                           portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var density, drift, threat, lightning, height;
    var cloudBase, cloudLayers, lightningFlash, rumble;
    var driftRate, filterMod;

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
    density = In.kr(customBus0);
    drift = In.kr(customBus1);
    threat = In.kr(customBus2);
    lightning = In.kr(customBus3);
    height = In.kr(customBus4);

    driftRate = drift.linexp(0, 1, 0.02, 0.3);

    // Base cloud - filtered noise at altitude-dependent frequency
    cloudBase = PinkNoise.ar(density * 0.5);
    cloudBase = LPF.ar(cloudBase, freq * height.linlin(0, 1, 0.5, 2));

    // Multiple cloud layers with different movement
    cloudLayers = Mix.fill(4, { |i|
        var layerRate = driftRate * (1 + (i * 0.3));
        var layerNoise = GrayNoise.ar(density * 0.2 / (i + 1));
        var layerFreq = freq * (0.5 + (height * i * 0.3));
        BPF.ar(layerNoise, 
            layerFreq * LFNoise1.kr(layerRate).range(0.7, 1.3),
            0.5
        );
    });

    // Threat - low rumbling darkness
    rumble = BrownNoise.ar(threat * 0.3);
    rumble = LPF.ar(rumble, freq * 0.5);
    rumble = rumble * LFNoise2.kr(driftRate * 0.5).range(0.5, 1);

    // Lightning flashes - sudden bright bursts
    lightningFlash = WhiteNoise.ar(1) * 
        EnvGen.ar(
            Env.perc(0.001, 0.05),
            Dust.kr(lightning.linlin(0, 1, 0.1, 2))
        ) * lightning * 0.5;
    lightningFlash = HPF.ar(lightningFlash, 2000);

    // Filter modulation - clouds shifting
    filterMod = LFNoise1.kr(driftRate).range(
        freq * (1 - (threat * 0.5)),
        freq * (2 + height)
    );

    // Combine
    sig = cloudBase + cloudLayers + rumble + lightningFlash;

    // Apply drift filter
    sig = RLPF.ar(sig, filterMod, 0.4);

    // Stereo spread - wide clouds
    sig = ~stereoSpread.(sig, driftRate, 0.7);

    // Standard output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_drangarnir_storm_cloud loaded".postln;
