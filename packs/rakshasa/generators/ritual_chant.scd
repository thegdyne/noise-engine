// Ritual Chant -- Formant vocal synthesis for invocations
// Role: foreground | Family: physical

SynthDef(\forge_rakshasa_ritual_chant, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                          filterTypeBus, envEnabledBus, envSourceBus=0,
                                          clockRateBus, clockTrigBus,
                                          midiTrigBus=0, slotIndex=0,
                                          customBus0, customBus1, customBus2, customBus3, customBus4,
                                          portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var vox, wail, summon, prayer, spirit;
    var source, formants, formantFreqs, vibrato, drift, breath;
    var harmonics;

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

    // Custom parameters
    vox = In.kr(customBus0);                               // Formant blend (0-1)
    wail = In.kr(customBus1).linlin(0, 1, 0, 0.08);        // Vibrato depth
    summon = In.kr(customBus2).linlin(0, 1, 0, 0.15);      // Pitch drift amount
    prayer = In.kr(customBus3).linlin(0, 1, 1, 6);         // Number of harmonics
    spirit = In.kr(customBus4).linlin(0, 1, 0, 0.4);       // Breathiness

    // Vibrato for wailing
    vibrato = SinOsc.kr(5 + LFNoise1.kr(0.3).range(0, 2)) * wail;

    // Slow pitch drift for summoning
    drift = LFNoise1.kr(0.1) * summon;

    // Apply pitch modulations
    freq = freq * (1 + vibrato + drift);

    // Source -- rich pulse wave for vocal cord simulation
    source = Pulse.ar(freq, 0.3 + (LFNoise1.kr(1) * 0.1));

    // Add harmonics for prayer complexity
    harmonics = Mix.fill(8, { |i|
        var harm, ampScale;
        ampScale = ((prayer * 8) > i).asInteger;
        harm = Pulse.ar(freq * (i + 1), 0.5 - (i * 0.05).clip(0, 0.4));
        harm * (1 / ((i + 1) * 2)) * ampScale
    });
    source = source + (harmonics * 0.3);

    // Formant frequencies -- morphs between vowels based on vox
    // Dark (O/U) at 0, bright (I/E/A) at 1
    formantFreqs = [
        vox.linlin(0, 1, 300, 800),   // F1
        vox.linlin(0, 1, 800, 2300),  // F2
        vox.linlin(0, 1, 2300, 3000)  // F3
    ];

    // Apply formant filters
    formants = Mix.ar(
        formantFreqs.collect({ |f, i|
            BPF.ar(source, f.clip(80, 10000), 0.1) * [0.8, 0.5, 0.3][i]
        })
    );

    // Breath/spirit layer
    breath = BPF.ar(PinkNoise.ar, formantFreqs[1], 0.3) * spirit;
    breath = breath * LFNoise2.kr(3).range(0.5, 1);

    sig = formants + breath;

    // Subtle stereo
    sig = Pan2.ar(sig, LFNoise2.kr(0.5).range(-0.2, 0.2));

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp,
                   clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_rakshasa_ritual_chant loaded".postln;
