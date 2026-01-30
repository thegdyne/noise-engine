// core/karplus_strong — Lightweight end-stage generator
/*
Karplus-Strong Generator
Physical modeling string/pluck synthesis

Signal flow: Exciter -> Delay Loop -> Filter -> ENV VCA -> Output

Custom params:
  - P1 exciter_color: 0-1 (dark thump <-> bright click)
  - P2 damping: 0-1 (string brightness/decay)
  - P3 feedback: 0.9-0.999 (sustain length)
  - P4 stretch: 0-1 (inharmonicity)
  - P5 retrig_rate: 0.1-50 Hz (internal pluck rate)

MIDI retrig mode: When envSource=MIDI, external triggers drive the exciter
at ~30Hz while key is held. The retrig_rate param is ignored in this mode.
*/

SynthDef(\karplusStrong, { |out, freqBus, customBus0|
    var sig, freq;
    var p = In.kr(customBus0, 5);
    var excColor, lpfCoeff, fbGain, stretch, retrigRate;
    var exciter, delayTime, delayed, loopSig, loopFilter, exciterTrig;
    var allMidiTrigs, midiTrig;

    freq = In.kr(freqBus);

    excColor = p[0];
    lpfCoeff = p[1];
    fbGain = p[2];
    stretch = p[3];
    retrigRate = p[4];

    // === EXCITER TRIGGER ===
    // In MIDI mode (envSource=2), use MIDI trigger bus (continuous 30Hz from held key)
    // Otherwise use internal retrig rate
    allMidiTrigs = In.ar(midiTrigBus, 8);
    midiTrig = Select.ar(slotIndex, allMidiTrigs);

    exciterTrig = Select.ar(envSource > 1, [
        Impulse.ar(retrigRate),  // Internal retrig (envSource 0 or 1)
        midiTrig                  // MIDI retrig (envSource 2)
    ]);

    // === SOUND SOURCE ===
    delayTime = (1 / freq.clip(20, 8000)) * stretch.linlin(0, 1, 1, 1.02);
    delayTime = delayTime.clip(0.00005, 0.05);

    exciter = SelectX.ar(excColor, [
        PinkNoise.ar * EnvGen.ar(Env.perc(0.001, 0.02), exciterTrig),
        (Impulse.ar(0) + (WhiteNoise.ar * 0.7)) * EnvGen.ar(Env.perc(0.0001, 0.01), exciterTrig)
    ]);

    loopSig = LocalIn.ar(1);
    delayed = DelayC.ar(exciter + loopSig, 0.05, delayTime);
    loopFilter = LPF.ar(delayed, lpfCoeff.linexp(0, 1, 500, 12000));
    loopFilter = loopFilter * fbGain;
    LocalOut.ar(loopFilter);

    sig = delayed;

    sig = ~stereoSpread.(sig, 0.3, 0.2);
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] karplusStrong loaded".postln;
