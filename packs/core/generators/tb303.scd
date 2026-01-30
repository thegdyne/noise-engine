// core/tb303 — Lightweight end-stage generator
/*
TB-303 Generator
Roland TB-303 Bassline inspired acid synth

Features:
  - Saw or square oscillator
  - Classic 303 diode ladder filter character
  - Accent (boosts resonance + volume + env depth)
  - Snappy filter envelope with adjustable decay
  - Slide/glide between notes
  - That squelchy acid sound!

Custom params:
  - P1 waveform: 0=saw, 1=square
  - P2 accent: Accent intensity
  - P3 env_mod: Filter envelope depth
  - P4 env_decay: Filter envelope decay time
  - P5 slide: Portamento/glide amount
*/

SynthDef(\tb303, { |out, freqBus, customBus0|
    var sig, freq;
    var p = In.kr(customBus0, 5);
    var waveform, accent, envMod, envDecay, slide;
    var slidingFreq, saw, square;

    freq = In.kr(freqBus);

    waveform = p[0];
    accent = p[1];
    accent = Lag.kr(accent, 0.02);  // Smooth accent changes to prevent zipper noise
    envMod = p[2];
    envDecay = p[3];
    slide = p[4];

    // === SLIDE (Portamento) ===
    // Squared mapping gives more resolution in short glides (the musical sweet spot)
    slidingFreq = Lag.kr(freq, slide.squared * 0.3);

    // === VCO ===
    saw = Saw.ar(slidingFreq);
    square = Pulse.ar(slidingFreq, 0.5);
    sig = SelectX.ar(waveform, [saw, square]);

    // Add some soft saturation for that gritty 303 character
    sig = (sig * 2).tanh * 0.7;

    // === OUTPUT ===
    sig = ~stereoSpread.(sig, 0.05, 0.05);  // Minimal stereo - 303 is mono
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] tb303 loaded".postln;
