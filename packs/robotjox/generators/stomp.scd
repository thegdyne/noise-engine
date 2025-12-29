SynthDef(\forge_robotjox_stomp, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                    filterTypeBus, envEnabledBus, envSourceBus=0,
                                    clockRateBus, clockTrigBus,
                                    midiTrigBus=0, slotIndex=0,
                                    customBus0, customBus1, customBus2, customBus3, customBus4,
                                    portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, envSource, clockRate, portamento;
    var mass, ground, quake, debris, pace;
    var trig, impact, membrane, subBoom, debrisNoise, rumble;

    // Theme params
    mass = In.kr(customBus0);
    ground = In.kr(customBus1);
    quake = In.kr(customBus2);
    debris = In.kr(customBus3);
    pace = In.kr(customBus4);

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

    // Step trigger
    trig = Dust.ar(pace.linexp(0, 1, 0.5, 4));

    // Impact transient
    impact = HPF.ar(WhiteNoise.ar(0.8), 100) * Decay.ar(trig, 0.02);
    impact = impact + (BrownNoise.ar(0.5) * Decay.ar(trig, 0.05));

    // Membrane resonance - ground surface
    membrane = Ringz.ar(trig, freq * (0.5 + (ground * 0.5)), 0.2 + (mass * 0.3), 0.4);
    membrane = membrane + Ringz.ar(trig, freq * 0.7, 0.15 + (mass * 0.2), 0.3);
    membrane = membrane + Ringz.ar(trig, freq * 1.3, 0.1 + (ground * 0.15), 0.25);

    // Sub boom - massive weight
    subBoom = SinOsc.ar(freq * 0.25, 0, 0.5 * mass);
    subBoom = subBoom * Decay.ar(trig, 0.3 + (mass * 0.4));
    subBoom = subBoom + (SinOsc.ar(freq * 0.125, 0, 0.3 * mass) * Decay.ar(trig, 0.5));

    // Debris scatter
    debrisNoise = HPF.ar(PinkNoise.ar(0.4), 1000);
    debrisNoise = debrisNoise * Decay2.ar(trig, 0.01, 0.2 + (debris * 0.3));
    debrisNoise = debrisNoise * debris;

    sig = impact + membrane + subBoom + debrisNoise;

    // Continuous ground rumble
    rumble = LPF.ar(BrownNoise.ar(0.2), 100 + (freq * 0.3));
    rumble = rumble * LFNoise2.kr(0.5).range(0.5, 1.0);
    rumble = rumble * (0.3 + (quake * 0.7));

    sig = sig + rumble;

    // Continuous bed
    sig = sig + LPF.ar(BrownNoise.ar(0.1), 200);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, 0.2, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_robotjox_stomp loaded".postln;
