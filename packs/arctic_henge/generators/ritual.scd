SynthDef(\forge_arctic_henge_ritual, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
    filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
    midiTrigBus=0, slotIndex=0,
    customBus0, customBus1, customBus2, customBus3, customBus4,
    portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var voice, chant, ancient, drone, spirit;
    var source, formants, breath, ghostly, vowelMod;
    var f1, f2, f3, bw;

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

    // Theme params
    voice = In.kr(customBus0);
    chant = In.kr(customBus1);
    ancient = In.kr(customBus2);
    drone = In.kr(customBus3);
    spirit = In.kr(customBus4);

    // Slow vowel modulation
    vowelMod = voice + (SinOsc.kr(chant.linexp(0, 1, 0.05, 0.5)) * chant * 0.3);
    vowelMod = vowelMod.clip(0, 1);

    // Formant frequencies (interpolating between vowels A-E-I-O-U)
    // A: 800, 1200, 2500  E: 400, 2000, 2800  I: 300, 2300, 3000
    // O: 500, 800, 2500   U: 350, 600, 2400
    f1 = vowelMod.linlin(0, 1, 300, 800);
    f2 = Select.kr((vowelMod * 4).round, [1200, 2000, 2300, 800, 600]);
    f3 = vowelMod.linlin(0, 1, 2400, 3000);
    bw = ancient.linexp(0, 1, 50, 200);

    // Source - pulse wave for vocal character
    source = Pulse.ar(freq, 0.3 + (ancient * 0.2)) * drone;
    source = source + (Saw.ar(freq * 1.003) * drone * 0.3);

    // Three formant filters
    formants = BPF.ar(source, f1, bw / f1) * 0.6;
    formants = formants + BPF.ar(source, f2, bw / f2) * 0.4;
    formants = formants + BPF.ar(source, f3, bw / f3) * 0.2;

    // Breath component
    breath = BPF.ar(
        PinkNoise.ar,
        vowelMod.linexp(0, 1, 500, 2000),
        0.3
    ) * ancient * 0.2;

    // Ghostly upper harmonics
    ghostly = Mix.fill(4, { |i|
        var ghostFreq = freq * (6 + i);
        SinOsc.ar(ghostFreq * (1 + (LFNoise1.kr(0.2) * 0.01))) *
        EnvGen.kr(Env.sine(4 + (i * 2))) * 0.03
    }) * spirit;

    sig = formants + breath + ghostly;

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_arctic_henge_ritual loaded".postln;
