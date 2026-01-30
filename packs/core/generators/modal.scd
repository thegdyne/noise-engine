// core/modal — Lightweight end-stage generator
/*
Modal Generator
Resonant body physical modeling

Signal flow: Exciter -> Modal Resonators -> Filter -> ENV VCA -> Output

Custom params:
  - P1 material: 0-1 (wood <-> metal <-> glass)
  - P2 brightness: 0-1 (muted <-> bright)
  - P3 decay_shape: 0-1 (quick <-> ringing)
  - P4 density: 1-20 (number of modes)
  - P5 retrig_rate: 0.1-50 Hz (internal strike rate)

MIDI retrig mode: When envSource=MIDI, external triggers drive the exciter
at ~30Hz while key is held. The retrig_rate param is ignored in this mode.
*/

SynthDef(\modal, { |out, freqBus, customBus0|
    var sig, freq;
    var p = In.kr(customBus0, 5);
    var material, brightness, decayShape, density, retrigRate;
    var exciter, modes, exciterTrig;

    freq = In.kr(freqBus);

    material = p[0];
    brightness = p[1];
    decayShape = p[2];
    density = p[3];
    retrigRate = p[4];

    // Internal retrig rate (end-stage handles envelope/retriggering)
    exciterTrig = Impulse.ar(retrigRate);

    // === SOUND SOURCE ===
    exciter = WhiteNoise.ar * EnvGen.ar(Env.perc(0.0001, 0.005), exciterTrig);

    modes = Mix.fill(12, { |i|
        var modeFreq, modeAmp, modeDecay, ratio;
        ratio = [1, 2.0, 3.0, 4.2, 5.4, 6.8, 8.2, 9.8, 11.5, 13.3, 15.2, 17.3][i];
        ratio = ratio * material.linlin(0, 1, 0.95, 1.05);
        modeFreq = (freq * ratio).clip(20, 18000);
        modeAmp = (1 / (i + 1)) * (1 - (material * 0.3 * i / 12));
        modeDecay = decayShape.linexp(0, 1, 0.05, 2) / (i + 1);

        Ringz.ar(exciter, modeFreq, modeDecay) * modeAmp * (i < density)
    }) * brightness.linlin(0, 1, 0.3, 1);

    sig = modes * 0.2;

    sig = ~stereoSpread.(sig, 0.15, 0.4);
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] modal loaded".postln;
