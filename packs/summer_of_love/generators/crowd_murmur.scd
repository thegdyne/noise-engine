SynthDef(\forge_summer_of_love_crowd_murmur, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                                 filterTypeBus, envEnabledBus, envSourceBus=0,
                                                 clockRateBus, clockTrigBus,
                                                 midiTrigBus=0, slotIndex=0,
                                                 customBus0, customBus1, customBus2, customBus3, customBus4,
                                                 portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var density, distance, mood, movement, space;
    var noise, formants, formantFreqs, formantMods, distanceFilter;

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
    density = In.kr(customBus0);    // Voice density
    distance = In.kr(customBus1);   // Near/far (affects brightness)
    mood = In.kr(customBus2);       // Relaxed to excited
    movement = In.kr(customBus3);   // Formant modulation
    space = In.kr(customBus4);      // Stereo width

    // Base noise source - pink for more natural voice-like spectrum
    noise = PinkNoise.ar(1) + (BrownNoise.ar(0.3) * (1 - mood));

    // Formant frequencies - speech-like bands shifted by mood and freq
    formantFreqs = [
        freq * 1.0,   // F1 - low vowel formant
        freq * 2.5,   // F2 - mid vowel formant
        freq * 4.0,   // F3 - high formant
        freq * 6.0    // F4 - presence
    ];

    // Movement modulation on formants
    formantMods = formantFreqs.collect({ |f, i|
        var modRate = 0.1 + (movement * 0.5) + (i * 0.05);
        var modDepth = movement * 0.15;
        f * (1 + (LFNoise1.kr(modRate) * modDepth))
    });

    // Create formant bands with resonant bandpass filters
    formants = formantMods.collect({ |f, i|
        var bw = f * 0.3;  // Bandwidth
        var gain = [1.0, 0.7, 0.4, 0.2][i] * density;
        BPF.ar(noise, f.clip(100, 8000), 0.2) * gain
    }).sum;

    // Add some impulse-like energy for consonants
    formants = formants + (Dust.ar(density.linlin(0, 1, 5, 30)) * BPF.ar(WhiteNoise.ar(0.1), 2500, 0.5) * density);

    sig = formants;

    // Distance filter - further = darker
    distanceFilter = distance.linexp(0, 1, 8000, 1500);
    sig = LPF.ar(sig, distanceFilter);

    // Add subtle room character for distance
    sig = sig + (CombL.ar(sig, 0.1, distance.linlin(0, 1, 0.01, 0.05), distance * 0.5) * distance * 0.3);

    // Stereo spread for space
    sig = ~stereoSpread.(sig, 0.15 + (movement * 0.2), space * 0.8);

    // Apply standard processing chain
    sig = sig * 4;  // gain boost
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;
"  * forge_summer_of_love_crowd_murmur loaded".postln;
