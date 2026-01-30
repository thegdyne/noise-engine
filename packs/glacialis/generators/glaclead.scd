// glacialis/glaclead — Lightweight end-stage generator
// GLACLEAD - Crystalline melodic lead
// Phase modulation with faceted detuning

SynthDef(\forge_glacialis_glaclead, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var ice, facet, prism, melt, glass;
    var carrier, modulator, detuned, harmonics, lfo;

    ice = p[0];  // Brightness
    facet = p[1];  // Detuning
    prism = p[2];  // PM depth
    melt = p[3];  // Filter env
    glass = p[4];  // Harmonic emphasis

    freq = In.kr(freqBus);

    // Subtle shimmer LFO
    lfo = SinOsc.kr(4 + (ice * 3)).range(0.98, 1.02);

    // Phase modulation - carrier with modulator
    modulator = SinOsc.ar(freq * 2) * prism.linexp(0, 1, 0.5, 4) * freq;
    carrier = SinOsc.ar(freq + modulator);

    // Faceted detuning - multiple slightly detuned copies
    detuned = Mix.fill(4, { |i|
        var detune, phase;
        detune = facet.linexp(0, 1, 1, 1.01) ** (i - 1.5);
        phase = i * 0.25 * pi;
        SinOsc.ar((freq * detune * lfo) + (modulator * (1 - (i * 0.15))), phase)
    }) * 0.3;

    sig = (carrier * 0.4) + detuned;

    // Glassy harmonics - add upper partials
    harmonics = SinOsc.ar(freq * 3, SinOsc.ar(freq * 5) * glass) * 0.2;
    harmonics = harmonics + (SinOsc.ar(freq * 5) * 0.1);
    sig = sig + (harmonics * glass);

    // Brightness control via high shelf
    sig = sig + (HPF.ar(sig, 2000) * ice * 0.5);

    // Subtle stereo from facet
    sig = [sig, DelayC.ar(sig, 0.01, facet * 0.003)];

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_glacialis_glaclead loaded".postln;
