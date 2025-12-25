// Countdown - Mission sequence tones with escalating tension
// Role: foreground (melodic)

SynthDef(\forge_astro_command_countdown, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                            filterTypeBus, envEnabledBus, envSourceBus=0,
                                            clockRateBus, clockTrigBus,
                                            midiTrigBus=0, slotIndex=0,
                                            customBus0, customBus1, customBus2, customBus3, customBus4,
                                            portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var seq, ten, zro, vox, drm;
    var seqRate, countTone, tensionRise, zeroBlast, vocoderChar;
    var seqTrig, pitchStep, dramaSwell;

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
    seq = In.kr(customBus0).linlin(0, 1, 0, 1);
    ten = In.kr(customBus1).linlin(0, 1, 0, 1);
    zro = In.kr(customBus2).linlin(0, 1, 0, 1);
    vox = In.kr(customBus3).linlin(0, 1, 0, 1);
    drm = In.kr(customBus4).linlin(0, 1, 0, 1);

    // Sequence rate
    seqRate = seq.linexp(0, 1, 0.5, 8);
    seqTrig = Impulse.ar(seqRate);

    // Stepped pitch movement (countdown feel)
    pitchStep = LFNoise0.kr(seqRate * 0.5).range(0, 1);

    // Main countdown tone - clean with harmonics
    countTone = Mix.ar([
        SinOsc.ar(freq * (1 + (pitchStep * ten * 0.5)), 0, 0.5),
        SinOsc.ar(freq * 2 * (1 + (pitchStep * ten * 0.3)), 0, 0.2),
        Pulse.ar(freq * (1 + (pitchStep * ten * 0.5)), 0.3, 0.15)
    ]);

    // Apply sequence envelope
    countTone = countTone * EnvGen.ar(
        Env.perc(0.005, seq.linlin(0, 1, 0.3, 0.1)),
        seqTrig
    );

    // Tension rise - ascending background
    tensionRise = SinOsc.ar(
        freq * 0.5 * (1 + (LFSaw.kr(seqRate * 0.125).range(0, ten)))
    ) * ten * 0.3;

    // Zero-point blast - dramatic low frequency
    zeroBlast = SinOsc.ar(freq * 0.25) *
        EnvGen.ar(
            Env.perc(0.01, zro.linlin(0, 1, 0.2, 1)),
            Impulse.ar(seqRate * 0.25)
        ) * zro * 0.4;

    // Vocoder character - formant-like filtering
    vocoderChar = BPF.ar(
        countTone,
        [300, 800, 1200, 2400] * (1 + (pitchStep * 0.3)),
        0.3
    ).sum * vox;

    // Drama swell - slow building intensity
    dramaSwell = LFTri.kr(seqRate * 0.0625).range(1, 1 + (drm * 0.5));

    // Combine
    sig = (countTone + tensionRise + zeroBlast).blend(vocoderChar, vox * 0.5);
    sig = sig * dramaSwell;

    // Add urgency harmonics at high drama
    sig = sig + (
        Pulse.ar(freq * 4, 0.1) *
        LFPulse.ar(seqRate * 2, 0, 0.1) *
        drm * 0.1
    );

    // Output chain
    sig = ~stereoSpread.(sig, 0.2, 0.3);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  * forge_astro_command_countdown loaded".postln;
