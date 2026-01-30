// core/snare_808 — Lightweight end-stage generator
/*
808 Snare Generator
Classic TR-808 style snare drum

Features:
  - Two-tone sine body with pitch envelope
  - Filtered noise for snare wires
  - Separate decay controls for body and noise
  - Snap/transient control

Custom params:
  - P1 tone_level: Body/tone amount
  - P2 noise_level: Snare noise amount
  - P3 snap: Attack snap intensity
  - P4 tone_decay: Body decay time
  - P5 noise_decay: Noise decay time
*/

SynthDef(\snare_808, { |out, freqBus, customBus0|
    var sig, freq;
    var p = In.kr(customBus0, 5);
    var toneLevel, noiseLevel, snap, toneDecay, noiseDecay;
    var trig, pitchEnv, toneEnv, noiseEnv;
    var tone1, tone2, body, snareNoise;

    freq = In.kr(freqBus);

    toneLevel = p[0];
    noiseLevel = p[1];
    snap = p[2];
    toneDecay = p[3];
    noiseDecay = p[4];

    // One-shot trigger (end-stage handles retriggering)
    trig = Impulse.ar(0);

    // === ENVELOPES ===
    pitchEnv = EnvGen.ar(
        Env.perc(0.001, 0.03, 1, -8),
        trig
    );

    toneEnv = EnvGen.ar(
        Env.perc(0.001, toneDecay, 1, -6),
        trig
    );

    noiseEnv = EnvGen.ar(
        Env.perc(0.001, noiseDecay, 1, -4),
        trig
    );

    // === TONE BODY ===
    // 808 snare has two tones around 180Hz and 330Hz
    tone1 = SinOsc.ar(freq + (pitchEnv * freq * snap * 2)) * 0.7;
    tone2 = SinOsc.ar(freq * 1.8 + (pitchEnv * freq * snap)) * 0.5;
    body = (tone1 + tone2) * toneEnv * toneLevel;

    // === SNARE NOISE ===
    // Bandpassed noise for snare character
    snareNoise = WhiteNoise.ar;
    snareNoise = BPF.ar(snareNoise, 3000, 0.8) * 2;  // Boost bandpass
    snareNoise = HPF.ar(snareNoise, 500);  // Remove low rumble
    snareNoise = snareNoise * noiseEnv * noiseLevel;

    // === MIX ===
    sig = body + snareNoise;
    sig = sig.tanh;  // Soft clip

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] snare_808 loaded".postln;
