// sunken-temple/PilgrimStep — Lightweight end-stage generator
/*
PILGRIMSTEP Generator
Slow footsteps through flooded halls

Features:
  - Rhythmic footfall impacts
  - Water splash displacement
  - Heavy weighted steps
  - Hall reverb reflections

Custom params:
  - P1 pace: Step rhythm
  - P2 splash: Water splash
  - P3 weight: Impact heaviness
  - P4 echo: Hall reflections
  - P5 dread: Ominous drone
*/

SynthDef(\pilgrimstep, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var pace, splash, weight, echo, dread;
    var trig, stepTrig, stepSig, splashSig, weightSig, dreadSig;
    var stepEnv, stepRate;

    freq = In.kr(freqBus);

    pace = p[0];
    pace = Lag.kr(pace, 0.1);
    splash = p[1];
    splash = Lag.kr(splash, 0.05);
    weight = p[2];
    weight = Lag.kr(weight, 0.1);
    echo = p[3];
    echo = Lag.kr(echo, 0.1);
    dread = p[4];
    dread = Lag.kr(dread, 0.2);

    // === TRIGGER ===
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);

    // Step rhythm - slow walking pace
    stepRate = 0.8 + (pace * 1.2);  // 0.8 - 2 Hz
    stepTrig = trig + Impulse.ar(stepRate * LFNoise1.kr(0.3).range(0.9, 1.1));

    // === STEP (impact) ===
    stepEnv = EnvGen.ar(Env.perc(0.01, 0.15 + (weight * 0.1)), stepTrig);
    stepSig = BrownNoise.ar * stepEnv;
    stepSig = LPF.ar(stepSig, 300 + (weight * 200));
    // Thud resonance
    stepSig = stepSig + (SinOsc.ar(freq * 0.5) * stepEnv * weight * 0.5);
    stepSig = stepSig * 0.5;

    // === SPLASH (water) ===
    splashSig = WhiteNoise.ar * EnvGen.ar(Env.perc(0.001, 0.08), stepTrig);
    splashSig = BPF.ar(splashSig, 2000 + TRand.ar(-500, 500, stepTrig), 0.4);
    // Ripple
    splashSig = splashSig + (
        SinOsc.ar(freq * 4 * TRand.ar(0.8, 1.2, stepTrig)) *
        EnvGen.ar(Env.perc(0.01, 0.1), stepTrig) * 0.3
    );
    splashSig = splashSig * splash * 0.4;

    // === WEIGHT (heavy resonance) ===
    weightSig = SinOsc.ar(freq * 0.25);
    weightSig = weightSig * EnvGen.ar(Env.perc(0.02, 0.3), stepTrig);
    weightSig = LPF.ar(weightSig, 150);
    weightSig = weightSig * weight * 0.4;

    // === DREAD (undertone) ===
    dreadSig = SinOsc.ar(freq * 0.5 * LFNoise2.kr(0.1).range(0.98, 1.02));
    dreadSig = dreadSig + (SinOsc.ar(freq * 0.75) * 0.3);  // Dissonance
    dreadSig = LPF.ar(dreadSig, 200);
    dreadSig = dreadSig * dread * 0.3 * LFTri.kr(0.1).range(0.5, 1);

    // === MIX ===
    sig = stepSig + splashSig + weightSig + dreadSig;

    // === ECHO (hall) ===
    sig = sig + (CombL.ar(sig, 0.5, 0.23, echo * 3) * echo * 0.4);
    sig = sig + (CombL.ar(sig, 0.5, 0.31, echo * 2.5) * echo * 0.3);
    sig = sig + (CombL.ar(sig, 0.5, 0.17, echo * 2) * echo * 0.2);

    sig = sig.tanh;

    sig = ~stereoSpread.(sig, 0.2, 0.15);
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] pilgrimstep loaded".postln;
