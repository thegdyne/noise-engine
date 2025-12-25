// Fan Display - Iridescent shimmering pad like the peacock spider's display fan
// Layered detuned oscillators with chorus shimmer and spectral color

SynthDef(\forge_maratus_fan_display, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                        filterTypeBus, envEnabledBus, envSourceBus=0,
                                        clockRateBus, clockTrigBus,
                                        midiTrigBus=0, slotIndex=0,
                                        customBus0, customBus1, customBus2, customBus3, customBus4,
                                        portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var iridescence, fanWidth, hue, vibration, glow;
    var numVoices = 6;
    var detuneAmounts, voices, shimmerLFOs, hueFreq;

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
    iridescence = In.kr(customBus0).linlin(0, 1, 0.0, 0.03);  // Pitch shimmer depth
    fanWidth = In.kr(customBus1);  // Stereo spread
    hue = In.kr(customBus2);  // Spectral position
    vibration = In.kr(customBus3).linexp(0, 1, 0.5, 8);  // Tremolo rate
    glow = In.kr(customBus4);  // High harmonics

    // Detune spread for iridescent layers
    detuneAmounts = Array.fill(numVoices, { |i|
        (i - (numVoices - 1 / 2)) * 0.008  // Spread around center
    });

    // Generate shimmering voices with individual LFOs
    voices = numVoices.collect({ |i|
        var voiceFreq, shimmer, oscMix;
        shimmer = SinOsc.kr(
            vibration * (1 + (i * 0.15)),  // Slightly different rates
            i * 0.5  // Phase offset
        ) * iridescence;
        voiceFreq = freq * (1 + detuneAmounts[i] + shimmer);

        // Mix saw and sine based on glow
        oscMix = (Saw.ar(voiceFreq) * glow) + (SinOsc.ar(voiceFreq) * (1 - glow));
        oscMix
    });

    sig = Mix.ar(voices) / numVoices;

    // Hue shifts the spectral emphasis via resonant peak
    hueFreq = freq * hue.linexp(0, 1, 1.5, 6);
    sig = sig + (BPF.ar(sig, hueFreq.clip(100, 12000), 0.3) * 0.5);

    // Apply glow - add harmonics via soft saturation
    sig = (sig * (1 + (glow * 2))).tanh * 0.7;

    // Stereo spread based on fan width
    sig = ~stereoSpread.(sig, 0.2, fanWidth * 0.8);

    // Mandatory output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_maratus_fan_display loaded".postln;
