/*
FX Slot: Echo - Tape Delay
UI Refresh Phase 1 - Canonical FX slot pattern

Adapted from tape_echo.scd to use generic p1-p4 parameters.

Parameter mapping:
  p1 = Time (0-1 -> 50-500ms)
  p2 = Feedback (0-1)
  p3 = Tone (0-1 -> LPF freq)
  p4 = Wow/Flutter (0-1)
  return = Return level
  bypass = Bypass toggle
*/

SynthDef(\fxSlot_echo, { |inBus, outBus,
                          p1=0.3, p2=0.3, p3=0.7, p4=0.1,
                          returnLevel=0.5, bypass=0,
                          p1Bus=(-1), p2Bus=(-1), p3Bus=(-1), p4Bus=(-1)|
    var sig, delayed, fb, wowLfo, toneFreq;
    var dry, wet, output;
    var timeEff, feedbackEff, toneEff, wowEff;

    // Bus unification support
    timeEff = Select.kr(p1Bus >= 0, [p1, In.kr(p1Bus)]);
    feedbackEff = Select.kr(p2Bus >= 0, [p2, In.kr(p2Bus)]);
    toneEff = Select.kr(p3Bus >= 0, [p3, In.kr(p3Bus)]);
    wowEff = Select.kr(p4Bus >= 0, [p4, In.kr(p4Bus)]);

    // Smooth params
    timeEff = Lag.kr(timeEff, 0.05);
    feedbackEff = Lag.kr(feedbackEff, 0.02);
    toneEff = Lag.kr(toneEff, 0.02);
    wowEff = Lag.kr(wowEff, 0.02);

    // Map p1 (time): 0-1 -> 50-500ms
    timeEff = timeEff.linlin(0, 1, 0.05, 0.5);

    // Map p3 (tone): 0-1 -> 500-8000Hz LPF
    toneFreq = toneEff.linexp(0, 1, 500, 8000);

    // Wow LFO
    wowLfo = SinOsc.kr(LFNoise1.kr(0.2).range(0.5, 2)).range(0, 1) * wowEff * 0.002;

    // Read input
    sig = In.ar(inBus, 2);
    dry = sig;

    // Pre-emphasis
    sig = BHiShelf.ar(sig, 2000, 1, 2);

    // Feedback loop
    fb = LocalIn.ar(2);
    delayed = DelayC.ar(sig + (fb * feedbackEff.clip(0, 0.95)), 0.6, timeEff + wowLfo);

    // Tape saturation
    delayed = (delayed * 1.2).tanh * 0.9;

    // Progressive HF loss
    delayed = LPF.ar(delayed, toneFreq);

    LocalOut.ar(delayed);

    // Post-emphasis
    wet = BHiShelf.ar(delayed, 2000, 1, -2);

    // Apply return level
    wet = wet * Lag.kr(returnLevel, 0.02);

    // Bypass (crossfade)
    output = XFade2.ar(wet, dry * returnLevel, (Lag.kr(bypass, 0.02) * 2) - 1);

    Out.ar(outBus, output);
}).add;

"  [x] FX Slot: Echo SynthDef ready".postln;
