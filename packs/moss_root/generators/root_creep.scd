SynthDef(\forge_moss_root_root_creep, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                         filterTypeBus, envEnabledBus, envSourceBus=0,
                                         clockRateBus, clockTrigBus,
                                         midiTrigBus=0, slotIndex=0,
                                         customBus0, customBus1, customBus2, customBus3, customBus4,
                                         portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var twist, reach, tangle, earth, sky;
    var voices, earthSub, skyHarm, panMod;

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
    twist = In.kr(customBus0);
    reach = In.kr(customBus1);
    tangle = In.kr(customBus2);
    earth = In.kr(customBus3);
    sky = In.kr(customBus4);

    // Multiple tangled voices with independent slow modulation
    voices = Mix(Array.fill(4, { |i|
        var rate = twist.linexp(0, 1, 0.02, 0.3) * (1 + (i * 0.15));
        var pitchMod = LFNoise1.kr(rate) * reach.linlin(0, 1, 0.01, 0.08);
        var ampMod = LFNoise1.kr(rate * 0.7).range(0.3, 1);
        var voiceFreq = freq * (1 + pitchMod) * [1, 1.002, 0.998, 1.005][i];

        // Mix of saw and triangle for organic character
        var voice = (Saw.ar(voiceFreq) * 0.6) + (LFTri.ar(voiceFreq) * 0.4);
        voice * ampMod * (tangle.linlin(0, 1, 0.3, 1) / 4)
    }));

    // Earth: sub oscillator rooted deep
    earthSub = SinOsc.ar(freq * 0.5) * earth * 0.4;
    earthSub = earthSub + (LFTri.ar(freq * 0.25) * earth * 0.2);

    // Sky: upper harmonics reaching up
    skyHarm = Mix([
        SinOsc.ar(freq * 2, LFNoise1.kr(twist.linexp(0, 1, 0.1, 0.5)) * sky),
        SinOsc.ar(freq * 3) * 0.5,
        SinOsc.ar(freq * 4) * 0.3
    ]) * sky * 0.15;
    // Sky has its own slow tremolo
    skyHarm = skyHarm * LFTri.kr(twist.linexp(0, 1, 0.5, 2)).range(0.6, 1);

    sig = voices + earthSub + skyHarm;

    // Slow stereo movement - roots spreading
    panMod = LFNoise1.kr(twist.linexp(0, 1, 0.05, 0.2));
    sig = Pan2.ar(sig, panMod * tangle * 0.7);

    // MANDATORY output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_moss_root_root_creep loaded".postln;
