// core/subtractive — Lightweight end-stage generator
/*
Subtractive Generator
Classic oscillator + filter synthesis

Signal flow: Oscillators -> Mix -> Filter -> ENV VCA -> Output

Custom params:
  - P1 osc_waveform: 0-3 (saw/square/tri/noise)
  - P2 sub_osc_level: 0-1 (sub oscillator amount)
  - P3 osc_mix: 0-1 (OSC1 <-> OSC2 crossfade)
  - P4 noise_amount: 0-1 (noise layer)
  - P5 filter_drive: 0-1 (pre-filter saturation)
*/

SynthDef(\subtractive, { |out, freqBus, customBus0|
    var sig, freq;
    var p = In.kr(customBus0, 5);
    var waveform, subLevel, oscMix, noiseAmt, drive;
    var osc1, osc2, sub, noise, saw, square, tri, noiseOsc;

    freq = In.kr(freqBus);

    waveform = p[0];
    subLevel = p[1];
    oscMix = p[2];
    noiseAmt = p[3];
    drive = p[4];

    // === SOUND SOURCE ===
    saw = Saw.ar(freq);
    square = Pulse.ar(freq, 0.5);
    tri = LFTri.ar(freq);
    noiseOsc = WhiteNoise.ar;

    osc1 = SelectX.ar(waveform, [saw, square, tri, noiseOsc]);
    osc2 = SelectX.ar(waveform, [
        Saw.ar(freq * 1.005),
        Pulse.ar(freq * 0.995, 0.45),
        LFTri.ar(freq * 1.003),
        PinkNoise.ar
    ]);

    sub = Pulse.ar(freq * 0.5, 0.5) * subLevel;
    noise = WhiteNoise.ar * noiseAmt * 0.5;

    sig = ((osc1 * (1 - oscMix)) + (osc2 * oscMix)) * 0.5;
    sig = sig + sub + noise;
    sig = (sig * (1 + (drive * 4))).tanh;

    sig = ~stereoSpread.(sig, 0.3, 0.3);
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] subtractive loaded".postln;
