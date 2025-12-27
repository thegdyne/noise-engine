// vapor: Fog rolling across the empty lot
SynthDef(\forge_vapor_station_vapor, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var density, drift, depth, diffuse, damp;

    // Theme params
    density = In.kr(customBus0).linlin(0, 1, 0.3, 1);      // P1: Fog density
    drift = In.kr(customBus1).linlin(0, 1, 0.02, 0.2);     // P2: Drift speed
    depth = In.kr(customBus2).linlin(0, 1, 0.5, 2);        // P3: Low frequency depth
    diffuse = In.kr(customBus3).linlin(0, 1, 0.1, 0.6);    // P4: High diffusion
    damp = In.kr(customBus4).linlin(0, 1, 200, 2000);      // P5: Damping frequency

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

    // DSP: Layered filtered noise for fog
    sig = LPF.ar(PinkNoise.ar(density), damp * LFNoise1.kr(drift).range(0.5, 1.5));
    sig = sig + (LPF.ar(BrownNoise.ar(depth * 0.5), freq * 2));

    // High diffusion shimmer
    sig = sig + (HPF.ar(PinkNoise.ar(diffuse * 0.3), 3000) * LFNoise1.kr(drift * 2).range(0.3, 1));

    // Subtle tonal anchor
    sig = sig + (SinOsc.ar(freq * [0.5, 0.501]) * density * 0.15);

    sig = sig * 0.35;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_vapor_station_vapor loaded".postln;
