/*
FX Slot: Chorus - Stereo Ensemble
UI Refresh Phase 1 - Canonical FX slot pattern

3-voice chorus with stereo spread.

Parameter mapping:
  p1 = Rate (0-1 -> 0.1-5Hz LFO rate)
  p2 = Depth (0-1 -> delay modulation depth)
  p3 = Mix (0-1 -> dry/wet balance)
  p4 = Spread (0-1 -> stereo width)
  return = Return level
  bypass = Bypass toggle
*/

SynthDef(\fxSlot_chorus, { |inBus, outBus,
                            p1=0.3, p2=0.5, p3=0.5, p4=0.7,
                            returnLevel=0.5, bypass=0,
                            p1Bus=(-1), p2Bus=(-1), p3Bus=(-1), p4Bus=(-1)|
    var sig, chorus1, chorus2, chorus3, wet;
    var dry, output;
    var rateEff, depthEff, mixEff, spreadEff;
    var lfo1, lfo2, lfo3;
    var delayTime, modDepth;

    // Bus unification support
    rateEff = Select.kr(p1Bus >= 0, [p1, In.kr(p1Bus)]);
    depthEff = Select.kr(p2Bus >= 0, [p2, In.kr(p2Bus)]);
    mixEff = Select.kr(p3Bus >= 0, [p3, In.kr(p3Bus)]);
    spreadEff = Select.kr(p4Bus >= 0, [p4, In.kr(p4Bus)]);

    // Smooth params
    rateEff = Lag.kr(rateEff, 0.02);
    depthEff = Lag.kr(depthEff, 0.02);
    mixEff = Lag.kr(mixEff, 0.02);
    spreadEff = Lag.kr(spreadEff, 0.02);

    // Map rate: 0-1 -> 0.1-5Hz
    rateEff = rateEff.linexp(0, 1, 0.1, 5);

    // Map depth to delay modulation (0-8ms)
    modDepth = depthEff * 0.008;

    // Base delay time
    delayTime = 0.015;  // 15ms base

    // Read input
    sig = In.ar(inBus, 2);
    dry = sig;

    // 3 LFOs with phase offsets
    lfo1 = SinOsc.kr(rateEff, 0);
    lfo2 = SinOsc.kr(rateEff, 2pi/3);
    lfo3 = SinOsc.kr(rateEff, 4pi/3);

    // 3 chorus voices with modulated delays
    chorus1 = DelayC.ar(sig, 0.05, delayTime + (lfo1 * modDepth));
    chorus2 = DelayC.ar(sig, 0.05, (delayTime * 1.1) + (lfo2 * modDepth));
    chorus3 = DelayC.ar(sig, 0.05, (delayTime * 0.9) + (lfo3 * modDepth));

    // Mix voices with stereo spread
    wet = [
        (chorus1[0] + (chorus2[0] * (1 - spreadEff)) + (chorus3[0] * spreadEff)) / 2,
        (chorus1[1] + (chorus2[1] * spreadEff) + (chorus3[1] * (1 - spreadEff))) / 2
    ];

    // Soft saturation to warm up
    wet = (wet * 1.1).tanh;

    // Mix dry/wet
    wet = (dry * (1 - mixEff)) + (wet * mixEff);

    // Apply return level
    wet = wet * Lag.kr(returnLevel, 0.02);

    // Bypass (crossfade)
    output = XFade2.ar(wet, dry * returnLevel, (Lag.kr(bypass, 0.02) * 2) - 1);

    Out.ar(outBus, output);
}).add;

"  [x] FX Slot: Chorus SynthDef ready".postln;
