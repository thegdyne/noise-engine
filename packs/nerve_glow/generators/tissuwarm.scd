// nerve_glow/tissuwarm — Lightweight end-stage generator
// TISSUWARM -- Warm tissue formant
// Organic, breathy, living tissue warmth -- amber glow

SynthDef(\forge_nerve_glow_tissuwarm, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var cellular, blood, organic, hum, glow;
    var source, formants, formantFreqs, formantBWs, breath, fundamental;

    // Standard bus reads
    freq = In.kr(freqBus);

    cellular = p[0].linlin(0, 1, 0, 4);  // Formant set morph
    blood = p[1].linexp(0, 1, 0.1, 3.0);  // Movement rate
    organic = p[2].linlin(0, 1, 0.0, 0.3);  // Formant drift
    hum = p[3].linlin(0, 1, 0.2, 0.8);  // Fundamental amount
    glow = p[4].linexp(0, 1, 1000, 8000);  // Air/brightness

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

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  * forge_nerve_glow_tissuwarm loaded".postln;
