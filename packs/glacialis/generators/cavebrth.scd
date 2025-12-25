// CAVEBRTH - Wind through ice tubes
// Breath-like noise with tube resonance and formants

SynthDef(\forge_glacialis_cavebrth, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                       filterTypeBus, envEnabledBus, envSourceBus=0,
                                       clockRateBus, clockTrigBus,
                                       midiTrigBus=0, slotIndex=0,
                                       customBus0, customBus1, customBus2, customBus3, customBus4,
                                       portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var blow, tube, turbulence, voice, cave;
    var noise, breath, tubeRes, formants, caveRes, lfo;

    // Theme params
    blow = In.kr(customBus0);       // Breath intensity
    tube = In.kr(customBus1);       // Tube resonance
    turbulence = In.kr(customBus2); // Turbulence
    voice = In.kr(customBus3);      // Formant
    cave = In.kr(customBus4);       // Cave depth

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

    // Slow modulation for natural breath
    lfo = SinOsc.kr(0.15 + (turbulence * 0.3)).range(0.7, 1);

    // Base breath noise
    noise = WhiteNoise.ar(1) + (PinkNoise.ar(1) * 0.5);
    noise = noise * blow * lfo;

    // Turbulence modulation
    noise = noise * (1 + (LFNoise2.ar(turbulence.linexp(0, 1, 1, 20)) * turbulence * 0.5));

    // Tube resonance (comb filter at pitch frequency)
    tubeRes = CombL.ar(noise, 0.1, freq.reciprocal, tube.linexp(0, 1, 0.05, 0.5));
    tubeRes = tubeRes + CombL.ar(noise, 0.1, (freq * 2).reciprocal, tube.linexp(0, 1, 0.03, 0.3)) * 0.5;
    breath = (noise * (1 - tube)) + (tubeRes * tube);

    // Vocal formants (oo/ah blend)
    formants = BPF.ar(noise, voice.linexp(0, 1, 300, 700), 0.1) * 3;
    formants = formants + (BPF.ar(noise, voice.linexp(0, 1, 800, 1200), 0.15) * 2);
    formants = formants + (BPF.ar(noise, voice.linexp(0, 1, 2300, 2800), 0.2));
    breath = breath + (formants * voice * 0.5);

    // Cave resonance - long reverberant delays
    caveRes = CombL.ar(breath, 0.3, 0.17, cave.linexp(0, 1, 0.3, 2));
    caveRes = caveRes + CombL.ar(breath, 0.3, 0.23, cave.linexp(0, 1, 0.25, 1.5)) * 0.7;
    sig = breath + (caveRes * cave * 0.4);

    // Stereo width
    sig = [
        sig + (DelayC.ar(sig, 0.05, 0.013) * cave * 0.3),
        sig + (DelayC.ar(sig, 0.05, 0.019) * cave * 0.3)
    ];

    // Remove DC offset from noise/comb content
    sig = LeakDC.ar(sig);

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_glacialis_cavebrth loaded".postln;
