// rib: Bone architecture - ribbed resonant structures
SynthDef(\forge_scorn_rib, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var bone, hollow, crack, tension, marrow;

    // Theme params
    bone = In.kr(customBus0).linlin(0, 1, 0.3, 1);          // P1: Bone resonance
    hollow = In.kr(customBus1).linlin(0, 1, 0.01, 0.05);    // P2: Hollow spacing
    crack = In.kr(customBus2).linlin(0, 1, 1, 8);           // P3: Crack/stress rate
    tension = In.kr(customBus3).linlin(0, 1, 0.2, 0.7);     // P4: Structural tension
    marrow = In.kr(customBus4).linlin(0, 1, 0.1, 0.5);      // P5: Inner marrow

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

    // DSP: Bone resonance - hollow comb
    sig = CombL.ar(PinkNoise.ar(bone * 0.3), 0.1, hollow, tension * 2);

    // Continuous bone tone
    sig = sig + (BPF.ar(Saw.ar(freq * [0.5, 1]), freq * 2, 0.3) * bone * 0.25);

    // Crack sounds - stress on structure
    sig = sig + (Ringz.ar(Dust.ar(crack) * 0.2, freq * [3, 5, 7], 0.05) * tension);

    // Marrow - deep inner warmth
    sig = sig + (LPF.ar(BrownNoise.ar(marrow * 0.3), 300));

    // Structural hum
    sig = sig + (SinOsc.ar(freq * [0.5, 1]) * tension * 0.2);

    sig = sig * 0.45;

    // Output chain (with Limiter for comb)
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_scorn_rib loaded".postln;
