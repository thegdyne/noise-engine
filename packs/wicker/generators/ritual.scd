SynthDef(\forge_wicker_ritual, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var drum, blood, bone, earth, fate;
    var drumMod, bloodMod, boneMod, earthMod, fateMod;
    var membrane, heartbeat, rattle, drone, strike;

    // Read custom params
    drum = In.kr(customBus0);      // P1: Drum tension - scaled by bone
    blood = In.kr(customBus1);     // P2: Blood pulse rate - curve set by fate
    bone = In.kr(customBus2);      // P3: Bone resonance - modulates drum AND earth
    earth = In.kr(customBus3);     // P4: Earth depth - feeds back to blood
    fate = In.kr(customBus4);      // P5: Fate inevitability - master doom axis

    // BUTTERFLY EFFECT: Cross-modulation network
    drumMod = drum * (0.4 + (bone * 0.6));
    bloodMod = blood.linexp(0, 1, 0.5, 6) * (1 + (earth * fate * 1.5));
    boneMod = bone * (1 + (fate.squared * 0.5));
    earthMod = earth * (0.35 + (drum * blood * 0.65));
    fateMod = fate * (1 + (bone * earth * 0.4));

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

    // DSP: Tribal ritual drums
    
    // Strike: continuous triggering
    strike = Dust.ar(bloodMod * 2 * [1, 1.1]) + (Impulse.ar(0) * 0.5);
    
    // Membrane: drum body simulation
    membrane = Ringz.ar(
        strike,
        freq * drumMod.linlin(0, 1, 0.8, 1.5) * [1, 1.47, 2.09, 2.56],
        boneMod.linlin(0, 1, 0.08, 0.3)
    ).sum * 0.3;
    membrane = membrane + (SinOsc.ar(freq * 0.5, 0, 0.15) * Decay.ar(strike.sum, 0.2));
    
    // Heartbeat: low foundation pulse
    heartbeat = SinOsc.ar(freq * [0.25, 0.5], 0, [0.2, 0.12]).sum;
    heartbeat = heartbeat * (1 + (SinOsc.kr(bloodMod * 0.3) * earthMod * 0.3));
    heartbeat = heartbeat + (LFPulse.ar(freq * 0.25, 0, 0.3) * 0.08 * fateMod);
    
    // Rattle: bone percussion
    rattle = Dust.ar(drumMod.linexp(0, 1, 3, 25) * [1, 0.9]);
    rattle = Ringz.ar(rattle, freq * [3.2, 5.1, 7.4, 9.8], 0.02).sum * 0.15;
    rattle = rattle * boneMod.linlin(0, 1, 0.3, 1);
    
    // Drone: earth rumble
    drone = BrownNoise.ar(0.15) + (LFNoise1.ar(earthMod * 5) * 0.1);
    drone = RLPF.ar(drone, freq * earthMod.linlin(0, 1, 0.5, 2), 0.4);
    drone = drone * earthMod.linlin(0, 1, 0.2, 0.7);
    
    // Mix based on fate (doom axis)
    sig = membrane + heartbeat + (rattle * fateMod.linlin(0, 1, 0.5, 1.2)) + (drone * (1 + (fateMod * 0.5)));
    
    // Doom reverb tail
    sig = sig + (CombL.ar(sig, 0.2, earthMod.linlin(0, 1, 0.05, 0.15), fateMod * 0.8) * 0.2);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_wicker_ritual loaded".postln;
