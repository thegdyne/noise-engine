// cthulhu: The Great Old One - massive eldritch presence rising
SynthDef(\forge_rlyeh_cthulhu, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var mass, geometry, dread, voice, dream;
    var subSig, geoSig, dreadSig, voiceSig, dreamSig;

    // Theme params
    mass = In.kr(customBus0).linlin(0, 1, 0.2, 1);         // P1: Sub-bass mass
    geometry = In.kr(customBus1).linlin(0, 1, 0, 0.5);     // P2: Non-Euclidean harmonics
    dread = In.kr(customBus2).linlin(0, 1, 0.1, 2);        // P3: Dread throb rate
    voice = In.kr(customBus3).linlin(0, 1, 0, 0.6);        // P4: Eldritch voice
    dream = In.kr(customBus4).linlin(0, 1, 0, 0.4);        // P5: Dream shimmer

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

    // DSP: Massive sub presence
    subSig = SinOsc.ar(freq / 2) + (SinOsc.ar(freq / 4) * 0.5);
    subSig = subSig * mass * LFNoise1.kr(0.1).range(0.7, 1);

    // Non-Euclidean geometry - impossible intervals
    geoSig = SinOsc.ar(freq * [1, 1.059, 1.189, 1.414]) * geometry;
    geoSig = Splay.ar(geoSig, 0.5) * 0.3;

    // Dread throb
    dreadSig = SinOsc.ar(freq) * SinOsc.kr(dread).range(0, 1) * 0.3;

    // Eldritch voice - formant drone
    voiceSig = Formant.ar(freq * 0.5, freq * 2 * LFNoise1.kr(0.2).range(0.8, 1.2), freq * 4) * voice * 0.2;

    // Dream transmission shimmer
    dreamSig = SinOsc.ar(freq * [3, 4.01, 5.02]) * LFNoise1.kr(0.3).range(0.3, 1) * dream * 0.15;
    dreamSig = Splay.ar(dreamSig, 0.7);

    sig = subSig + geoSig + dreadSig + voiceSig + dreamSig;
    sig = sig * 0.25;

    // Output chain (with Limiter for massive sub)
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_rlyeh_cthulhu loaded".postln;
