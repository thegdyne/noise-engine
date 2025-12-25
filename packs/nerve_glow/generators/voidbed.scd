// VOIDBED — Deep void background
// Dark filtered noise drone — the black space around the tissue

SynthDef(\forge_nerve_glow_voidbed, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                       filterTypeBus, envEnabledBus, envSourceBus=0,
                                       clockRateBus, clockTrigBus,
                                       midiTrigBus=0, slotIndex=0,
                                       customBus0, customBus1, customBus2, customBus3, customBus4,
                                       portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var depth, viscosity, darkness, flow, abyss;
    var noise, sub, movement, cutMod;

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

    // Custom params
    depth = In.kr(customBus0).linexp(0, 1, 100, 30);       // Base frequency (inverted for depth)
    viscosity = In.kr(customBus1).linexp(0, 1, 0.02, 0.5); // Filter movement rate
    darkness = In.kr(customBus2).linexp(0, 1, 4000, 200);  // HF cutoff (inverted)
    flow = In.kr(customBus3).linexp(0, 1, 0.05, 2.0);      // Internal modulation
    abyss = In.kr(customBus4).linlin(0, 1, 0.0, 0.8);      // Sub amount

    // Deep noise layers
    noise = BrownNoise.ar(0.5) + (PinkNoise.ar(0.2));

    // Slow filter movement
    cutMod = SinOsc.kr(flow, 0, 0.3, 1);
    noise = LPF.ar(noise, darkness * cutMod);
    noise = LPF.ar(noise, darkness * 0.5);  // Extra darkness

    // Resonant depth
    movement = BPF.ar(noise, freq.clip(20, 500), 0.2) * depth.reciprocal.linlin(30, 100, 0.5, 2);

    // Sub harmonic rumble
    sub = SinOsc.ar(freq * 0.5) * abyss * 0.3;
    sub = sub * LFNoise1.kr(viscosity).range(0.5, 1);

    sig = (noise * 0.4) + (movement * 0.4) + sub;

    // Very slow stereo drift
    sig = [
        DelayN.ar(sig, 0.05, SinOsc.kr(viscosity * 0.3, 0, 0.02, 0.025)),
        DelayN.ar(sig, 0.05, SinOsc.kr(viscosity * 0.3, pi, 0.02, 0.025))
    ];

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  * forge_nerve_glow_voidbed loaded".postln;
