// electric-shepherd/husk — Lightweight end-stage generator
/*
HUSK Generator
The empty shell - humanoid vessel being fed

Features:
  - Hollow breath through gas mask
  - Body cavity resonance
  - Servo/mechanical movement sounds
  - Filtered void (emptiness)
  - Involuntary twitches

Custom params:
  - P1 breath: Breath through mask/tube
  - P2 cavity: Hollow body resonance
  - P3 servo: Mechanical movement
  - P4 empty: Void/emptiness texture
  - P5 twitch: Involuntary movements

What remains when the soul is elsewhere.
*/

SynthDef(\husk, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var breath, cavity, servo, empty, twitch;
    var breathCycle;
    var breathSig, cavitySig, servoSig, emptySig, twitchSig;
    var breathNoise, breathMod;
    var cavityOsc, cavityExcite;
    var servoTrig, servoOsc;
    var emptyNoise, emptyMod;
    var twitchTrig, twitchOsc;

    freq = In.kr(freqBus);

    // Custom params with smoothing
    breath = p[0];
    breath = Lag.kr(breath, 0.05);
    cavity = p[1];
    cavity = Lag.kr(cavity, 0.05);
    servo = p[2];
    empty = p[3];
    empty = Lag.kr(empty, 0.1);
    twitch = p[4];

    // Breath cycle - slow inhale/exhale
    breathCycle = LFTri.kr(0.15).range(0, 1);

    // === BREATH (through mask) ===
    // Filtered noise shaped like breathing
    breathNoise = PinkNoise.ar;
    breathMod = breathCycle.squared;  // Sharper inhale shape
    breathSig = BPF.ar(breathNoise, 400 + (breathMod * 300), 0.3) * breathMod;
    breathSig = breathSig + (BPF.ar(breathNoise, 1200, 0.4) * breathMod * 0.5);  // Hiss
    // Mask resonance
    breathSig = breathSig + (Resonz.ar(breathNoise, 800, 0.1) * breathMod * 0.3);
    breathSig = breathSig * breath * 0.5;

    // === CAVITY (body resonance) ===
    // Hollow resonant drone
    cavityExcite = Dust.ar(3) + (breathNoise * 0.1);
    cavityOsc = Ringz.ar(cavityExcite, freq * 0.5, 0.5) * 0.3;
    cavityOsc = cavityOsc + (Ringz.ar(cavityExcite, freq * 0.75, 0.3) * 0.2);
    cavityOsc = cavityOsc + (Ringz.ar(cavityExcite, freq, 0.2) * 0.15);
    // Low body thrum
    cavityOsc = cavityOsc + (SinOsc.ar(freq * 0.25) * LFNoise2.kr(0.3).range(0.3, 0.7) * 0.3);
    cavitySig = LPF.ar(cavityOsc, 600) * cavity * 0.5;

    // === SERVO (mechanical movement) ===
    // Triggered mechanical sounds
    servoTrig = Dust.ar(servo * 3);
    servoOsc = SinOsc.ar(
        freq * 2 * EnvGen.ar(Env.perc(0.01, 0.1), servoTrig).linexp(0, 1, 0.5, 2)
    );
    servoOsc = servoOsc * EnvGen.ar(Env.perc(0.005, 0.15), servoTrig);
    // Add mechanical click
    servoOsc = servoOsc + (
        HPF.ar(WhiteNoise.ar, 2000) *
        EnvGen.ar(Env.perc(0.001, 0.02), servoTrig) * 0.5
    );
    servoSig = servoOsc * servo * 0.4;

    // === EMPTY (void texture) ===
    // Very filtered, distant, hollow
    emptyNoise = BrownNoise.ar;
    emptyMod = LFNoise2.kr(0.1).range(0.5, 1);
    emptySig = LPF.ar(emptyNoise, 100 + (empty * 100)) * emptyMod;
    // Add distant tone
    emptySig = emptySig + (SinOsc.ar(freq * 0.125) * 0.2 * emptyMod);
    emptySig = emptySig * empty * 0.4;

    // === TWITCH (involuntary) ===
    // Random sudden movements
    twitchTrig = Dust.ar(twitch * 5);
    twitchOsc = SinOsc.ar(freq * TRand.ar(1, 4, twitchTrig));
    twitchOsc = twitchOsc * EnvGen.ar(Env.perc(0.001, 0.05), twitchTrig);
    // Body thump
    twitchOsc = twitchOsc + (
        SinOsc.ar(freq * 0.25) *
        EnvGen.ar(Env.perc(0.001, 0.1), twitchTrig) * 0.5
    );
    twitchSig = twitchOsc * twitch * 0.3;

    // === MIX ===
    sig = breathSig + cavitySig + servoSig + emptySig + twitchSig;

    // Soft limiting
    sig = sig.tanh;

    sig = ~stereoSpread.(sig, 0.08, 0.2);
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] husk loaded".postln;
