// core/kick_808 — Lightweight end-stage generator
/*
808 Kick Generator
Classic TR-808 style kick drum

Features:
  - Sine oscillator with pitch envelope
  - Adjustable punch (pitch sweep depth)
  - Tone control (fundamental/harmonics balance)
  - Soft saturation for warmth
  - Click transient layer

Custom params:
  - P1 punch: Pitch envelope depth
  - P2 tone: Tone/body balance
  - P3 decay_time: Overall decay length
  - P4 drive: Saturation amount
  - P5 click: Click transient level
*/

SynthDef(\kick_808, { |out, freqBus, customBus0|
    var sig, freq;
    var p = In.kr(customBus0, 5);
    var punch, tone, decayTime, drive, click;
    var trig, pitchEnv, ampEnv, body, bodyWithHarmonics, clickSig, harmonics;

    freq = In.kr(freqBus);

    punch = p[0];
    tone = p[1];
    decayTime = p[2];
    drive = p[3];
    drive = Lag.kr(drive, 0.02);  // Smooth to prevent zipper noise
    click = p[4];

    // === TRIGGER ===
    // Clamp indices for safety
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);

    // === ENVELOPES ===
    // Pitch envelope - fixed fast time, punch controls depth only
    pitchEnv = EnvGen.ar(
        Env.perc(0.001, 0.06, 1, -8),  // Fixed 60ms decay for consistent 808 thump
        trig
    );

    // Amplitude envelope
    ampEnv = EnvGen.ar(
        Env.perc(0.001, decayTime, 1, -4),
        trig
    );

    // === SOUND SOURCE ===
    // Main body - sine with pitch sweep (punch = depth only)
    body = SinOsc.ar(freq + (pitchEnv * freq * punch * 4));

    // Harmonics for tone - slightly detuned 3rd partial for analog character
    harmonics = SinOsc.ar(freq * 2) * 0.3;
    harmonics = harmonics + (SinOsc.ar(freq * 2.98) * 0.1);  // Subtle inharmonicity

    // Body with harmonics mixed
    bodyWithHarmonics = body + harmonics;

    // Tone as true balance: crossfade from pure body to body+harmonics
    sig = XFade2.ar(body, bodyWithHarmonics, (tone * 2) - 1);

    // Apply amp envelope to body
    sig = sig * ampEnv;

    // Click transient - mixed post-ampEnv so it stays punchy
    clickSig = HPF.ar(WhiteNoise.ar, 1000) * EnvGen.ar(Env.perc(0.001, 0.015), trig);
    sig = sig + (clickSig * click);

    // === SATURATION ===
    sig = (sig * (1 + (drive * 3))).tanh;

    sig = sig * amp;
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] kick_808 loaded".postln;
