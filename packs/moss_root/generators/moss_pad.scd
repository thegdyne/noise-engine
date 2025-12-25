SynthDef(\forge_moss_root_moss_pad, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                        filterTypeBus, envEnabledBus, envSourceBus=0,
                                        clockRateBus, clockTrigBus,
                                        midiTrigBus=0, slotIndex=0,
                                        customBus0, customBus1, customBus2, customBus3, customBus4,
                                        portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var thickness, dampness, growth, scatter, sun;
    var voices, fuzz, bright, panPos;

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

    // Custom params
    thickness = In.kr(customBus0);
    dampness = In.kr(customBus1);
    growth = In.kr(customBus2);
    scatter = In.kr(customBus3);
    sun = In.kr(customBus4);

    // Multiple soft voices with subtle detuning
    voices = Mix(Array.fill(6, { |i|
        var detune = (i - 2.5) * 0.003 * thickness;
        var ampMod = LFNoise1.kr(growth.linexp(0, 1, 0.05, 0.4) + (i * 0.02));
        var voiceAmp = thickness.linlin(0, 1, 0.3, 1) / 6;
        SinOsc.ar(freq * (1 + detune)) * voiceAmp * ampMod.range(0.5, 1)
    }));

    // Add soft triangles for fullness
    voices = voices + (LFTri.ar(freq * 0.5) * 0.2 * thickness);

    // Fuzzy moss texture: filtered noise
    fuzz = LPF.ar(
        PinkNoise.ar(0.08 * thickness),
        freq * 4 * dampness.linexp(0, 1, 0.5, 2)
    );

    // Sunlight: bright harmonics via gentle FM
    bright = SinOsc.ar(
        freq * 2,
        SinOsc.ar(freq * 3) * sun.linlin(0, 1, 0, 1.5)
    ) * sun * 0.15;

    sig = voices + fuzz + bright;

    // Internal dampness filter (low-pass moss feeling)
    sig = LPF.ar(sig, dampness.linexp(0, 1, 8000, 1500));

    // Scatter: randomized stereo positioning
    panPos = LFNoise1.kr(scatter.linexp(0, 1, 0.1, 0.5)).range(scatter.neg * 0.8, scatter * 0.8);
    sig = Pan2.ar(sig, panPos);

    // MANDATORY output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_moss_root_moss_pad loaded".postln;
