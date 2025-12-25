// TARMAC - Desert floor drone, heat shimmer, wind across concrete
// Role: bed
SynthDef(\forge_boneyard_tarmac, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                    filterTypeBus, envEnabledBus, envSourceBus=0,
                                    clockRateBus, clockTrigBus,
                                    midiTrigBus=0, slotIndex=0,
                                    customBus0, customBus1, customBus2, customBus3, customBus4,
                                    portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var shimmer, density, cracks, distance, wind;
    var drone, sandNoise, crackImpulse, shimmerLFO, windLFO;

    // Custom params
    shimmer = In.kr(customBus0);    // Heat shimmer AM depth
    density = In.kr(customBus1);    // Sand grain density
    cracks = In.kr(customBus2);     // Concrete crack bursts
    distance = In.kr(customBus3);   // Distance filtering
    wind = In.kr(customBus4);       // Wind modulation rate

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

    // Wind modulation LFO - very slow, organic
    windLFO = LFNoise2.kr(wind.linexp(0, 1, 0.05, 0.8));

    // Heat shimmer - slow AM on the base drone
    shimmerLFO = SinOsc.kr(
        LFNoise1.kr(0.1).range(0.3, 2.0),
        0,
        shimmer * 0.5,
        1 - (shimmer * 0.25)
    );

    // Base drone - very low sine with subtle harmonics
    drone = SinOsc.ar(freq * 0.5, 0, 0.6);
    drone = drone + SinOsc.ar(freq, 0, 0.3);
    drone = drone + SinOsc.ar(freq * 1.5, 0, 0.1);
    drone = drone * shimmerLFO;

    // Sand noise - filtered noise with density control
    sandNoise = PinkNoise.ar(0.3);
    sandNoise = sandNoise + (Dust.ar(density.linexp(0, 1, 10, 500)) * 0.2);
    sandNoise = LPF.ar(sandNoise, density.linexp(0, 1, 200, 2000));
    sandNoise = HPF.ar(sandNoise, 80);
    sandNoise = sandNoise * (0.3 + (windLFO * 0.4));

    // Concrete cracks - random impulse bursts
    crackImpulse = Dust.ar(cracks.linexp(0, 1, 0.1, 8));
    crackImpulse = Ringz.ar(crackImpulse, freq * 2, 0.02, 0.4);
    crackImpulse = crackImpulse + (crackImpulse * BrownNoise.ar(0.3));

    // Combine layers
    sig = drone + sandNoise + crackImpulse;

    // Distance filtering - LP based on distance param
    sig = LPF.ar(sig, distance.linexp(0, 1, 8000, 800));
    sig = sig + (CombL.ar(sig, 0.3, 0.15, distance * 2) * distance * 0.3);

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_boneyard_tarmac loaded".postln;
