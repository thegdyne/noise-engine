// rakshasa/third_eye — Lightweight end-stage generator
// Third Eye -- Piercing hypnotic FM tone
// Role: foreground | Family: FM

SynthDef(\forge_rakshasa_third_eye, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var gaze, trance, sight, focus, pulse;
    var carrier, modulator, fmIndex, tranceMod, pulseMod;
    var harmonicMix, focusBand;

    // Standard bus reads
    freq = In.kr(freqBus);

    // Custom parameters
    gaze = p[0].linexp(0, 1, 0.5, 8);  // FM index / brightness
    trance = p[1].linlin(0, 1, 0, 0.4);  // Modulation depth
    sight = p[2].linlin(0, 1, 1, 5);  // Harmonic ratio
    focus = p[3].linlin(0, 1, 0.5, 0.05);  // Bandwidth (inverted)
    pulse = p[4].linexp(0, 1, 0.1, 8);  // Pulse rate

    // Trance modulation -- slow hypnotic movement
    tranceMod = SinOsc.kr(0.1 + (trance * 2)) * trance;

    // Pulse -- internal throb
    pulseMod = SinOsc.kr(pulse).range(1 - (trance * 0.3), 1);

    // FM index varies with gaze and trance
    fmIndex = gaze * (1 + tranceMod);

    // Modulator frequency based on sight (harmonic reach)
    modulator = SinOsc.ar(freq * sight * (1 + (tranceMod * 0.2)));

    // Carrier with FM
    carrier = SinOsc.ar(freq + (modulator * fmIndex * freq));

    // Add harmonics for piercing gaze
    harmonicMix = SinOsc.ar(freq * 2) * 0.3 * gaze.linlin(0.5, 8, 0, 1);
    harmonicMix = harmonicMix + (SinOsc.ar(freq * 3) * 0.15 * gaze.linlin(0.5, 8, 0, 1));

    sig = (carrier + harmonicMix) * pulseMod;

    // Focus -- bandpass for tight vs diffuse
    focusBand = BPF.ar(sig, freq * 1.5, focus);
    sig = (sig * (1 - focus.linlin(0.05, 0.5, 0.5, 0))) + (focusBand * focus.linlin(0.05, 0.5, 0.5, 0));

    // Stereo with subtle phase
    sig = [sig, DelayN.ar(sig, 0.01, 0.003)];

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  * forge_rakshasa_third_eye loaded".postln;
