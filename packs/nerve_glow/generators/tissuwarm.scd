// TISSUWARM -- Warm tissue formant
// Organic, breathy, living tissue warmth -- amber glow

SynthDef(\forge_nerve_glow_tissuwarm, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                         filterTypeBus, envEnabledBus, envSourceBus=0,
                                         clockRateBus, clockTrigBus,
                                         midiTrigBus=0, slotIndex=0,
                                         customBus0, customBus1, customBus2, customBus3, customBus4,
                                         portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var cellular, blood, organic, hum, glow;
    var source, formants, formantFreqs, formantBWs, breath, fundamental;

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
    cellular = In.kr(customBus0).linlin(0, 1, 0, 4);       // Formant set morph
    blood = In.kr(customBus1).linexp(0, 1, 0.1, 3.0);     // Movement rate
    organic = In.kr(customBus2).linlin(0, 1, 0.0, 0.3);   // Formant drift
    hum = In.kr(customBus3).linlin(0, 1, 0.2, 0.8);       // Fundamental amount
    glow = In.kr(customBus4).linexp(0, 1, 1000, 8000);    // Air/brightness

    // Source - mix of pulse and noise for organic excitation
    source = Pulse.ar(freq, 0.3, 0.5) + (PinkNoise.ar(0.3));

    // Formant frequencies based on cellular parameter (morphing vowels)
    // Moves through tissue-like formant sets
    formantFreqs = [
        cellular.linlin(0, 4, 300, 800),
        cellular.linlin(0, 4, 900, 1200),
        cellular.linlin(0, 4, 2400, 2800)
    ];

    // Add organic drift
    formantFreqs = formantFreqs * (1 + (SinOsc.kr(blood, [0, 1, 2], organic)));

    // Formant bandwidths
    formantBWs = [80, 100, 120];

    // Parallel formant filters
    formants = Mix.fill(3, { |i|
        var fFreq = formantFreqs[i];
        var bw = formantBWs[i];
        var amp = [1, 0.7, 0.4].at(i);
        BPF.ar(source, fFreq.clip(80, 12000), bw / fFreq) * amp
    });

    // Fundamental hum
    fundamental = SinOsc.ar(freq) * hum * 0.3;
    fundamental = fundamental * (1 + (SinOsc.kr(blood * 0.5, 0, 0.15)));

    // Breath/air component
    breath = HPF.ar(PinkNoise.ar(0.1), glow);
    breath = breath * LFNoise1.kr(blood).range(0.3, 1);

    sig = (formants * 0.5) + fundamental + (breath * 0.2);

    // Warm saturation
    sig = (sig * 1.5).tanh * 0.7;

    // Stereo spread
    sig = ~stereoSpread.(sig, 0.2, 0.25);

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  * forge_nerve_glow_tissuwarm loaded".postln;
