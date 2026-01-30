// core/wavetable — Lightweight end-stage generator
/*
Wavetable Generator
Interpolating wavetable synthesis with multiple waveforms

Signal flow: Wavetables -> Mix/Morph -> Filter -> ENV VCA -> Output

Custom params:
  - P1 wave_position: 0-1 (position in wavetable)
  - P2 wave_morph: 0-1 (crossfade between adjacent waves)
  - P3 detune: 0-1 (oscillator detuning)
  - P4 fold_amount: 0-1 (wavefolding)
  - P5 sub_level: 0-1 (sub oscillator)
*/

SynthDef(\wavetable, { |out, freqBus, customBus0|
    var sig, freq;
    var p = In.kr(customBus0, 5);
    var wavePos, morph, detune, fold, subLevel;
    var osc1, osc2, sub, wave1, wave2, wave3, wave4;

    freq = In.kr(freqBus);

    wavePos = p[0];
    morph = p[1];
    detune = p[2];
    fold = p[3];
    subLevel = p[4];

    // === SOUND SOURCE ===
    wave1 = SinOsc.ar(freq);
    wave2 = LFTri.ar(freq);
    wave3 = Saw.ar(freq);
    wave4 = Pulse.ar(freq, 0.5);

    osc1 = SelectX.ar(wavePos * 3, [wave1, wave2, wave3, wave4]);
    osc2 = SelectX.ar(wavePos * 3, [
        SinOsc.ar(freq * (1 + (detune * 0.02))),
        LFTri.ar(freq * (1 - (detune * 0.015))),
        Saw.ar(freq * (1 + (detune * 0.01))),
        Pulse.ar(freq * (1 - (detune * 0.02)), 0.45)
    ]);

    sig = (osc1 * (1 - morph)) + (osc2 * morph);
    sig = (sig * (1 + (fold * 4))).fold(-1, 1);

    sub = SinOsc.ar(freq * 0.5) * subLevel * 0.5;
    sig = sig + sub;

    sig = ~stereoSpread.(sig, 0.2, 0.3);
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] wavetable loaded".postln;
