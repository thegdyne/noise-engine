// summer_of_love/golden_haze — Lightweight end-stage generator
SynthDef(\forge_summer_of_love_golden_haze, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var warmth, drift, haze, layers, spread;
    var saws, driftLfo, detuneAmts, hazeFreq, saturated;

    freq = In.kr(freqBus);

    warmth = p[0];  // Even harmonics via soft saturation
    drift = p[1];  // Slow pitch wandering
    haze = p[2];  // High frequency softening
    layers = p[3];  // Voice count/thickness
    spread = p[4];  // Stereo width

    // Slow drift LFOs - different rates for organic movement
    driftLfo = LFNoise1.kr(0.1 + (drift * 0.3)) * (drift * 0.02);

    // Detune amounts for 7 voices
    detuneAmts = [-0.03, -0.02, -0.01, 0, 0.01, 0.02, 0.03];

    // Stack of detuned saws with drift
    saws = detuneAmts.collect({ |det, i|
        var voiceFreq, voiceDrift, pan;
        voiceDrift = LFNoise1.kr(0.05 + (i * 0.02)) * (drift * 0.015);
        voiceFreq = freq * (1 + det + driftLfo + voiceDrift);
        pan = (i - 3) / 3 * spread;
        Pan2.ar(Saw.ar(voiceFreq), pan)
    }).sum;

    // Layer mixing - fewer layers = thinner, more = thicker
    sig = saws * layers.linlin(0, 1, 0.4, 1.0);

    // Add sub for warmth foundation
    sig = sig + (SinOsc.ar(freq * 0.5) * warmth * 0.3);

    // Warmth saturation - soft clipping adds even harmonics
    saturated = (sig * (1 + (warmth * 2))).tanh;
    sig = XFade2.ar(sig, saturated, warmth.linlin(0, 1, -1, 0.5));

    // Haze filter - gentle lowpass that increases with haze param
    hazeFreq = haze.linexp(0, 1, 12000, 2000);
    sig = LPF.ar(sig, hazeFreq);

    // Apply standard processing chain

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_summer_of_love_golden_haze loaded".postln;
