// sunken-temple/ForgottenBreath — Lightweight end-stage generator
/*
FORGOTTENBREATH Generator
Wind through broken arches, breathy textures

Features:
  - Filtered wind noise
  - Archway resonance
  - Whispered textures
  - Dust and particle sounds

Custom params:
  - P1 wind: Wind intensity
  - P2 arch: Resonant openings
  - P3 whisper: Breathy voices
  - P4 dust: Particle texture
  - P5 sigh: Breathing rhythm
*/

SynthDef(\forgottenbreath, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var wind, arch, whisper, dust, sigh;
    var trig, windSig, archSig, whisperSig, dustSig, sighMod;
    var windNoise, archFreqs;

    freq = In.kr(freqBus);

    wind = p[0];
    wind = Lag.kr(wind, 0.2);
    arch = p[1];
    arch = Lag.kr(arch, 0.1);
    whisper = p[2];
    whisper = Lag.kr(whisper, 0.1);
    dust = p[3];
    dust = Lag.kr(dust, 0.05);
    sigh = p[4];
    sigh = Lag.kr(sigh, 0.2);

    // === TRIGGER ===
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);

    // Breathing modulation
    sighMod = LFTri.kr(0.15 + (sigh * 0.1)).range(0.3, 1);

    // === WIND (filtered noise) ===
    windNoise = PinkNoise.ar;
    windSig = BPF.ar(windNoise, 800 * LFNoise2.kr(0.5).range(0.5, 2), 0.4);
    windSig = windSig + (HPF.ar(windNoise, 3000) * 0.3);  // High whistling
    windSig = windSig * LFNoise1.kr(0.8 + wind).range(0.2, 1);  // Gusting
    windSig = windSig * wind * 0.4 * sighMod;

    // === ARCH (resonant openings) ===
    archFreqs = [1, 1.5, 2.2, 3.1] * freq;
    archSig = Mix.fill(4, { |i|
        var archF = archFreqs[i] * LFNoise2.kr(0.2).range(0.98, 1.02);
        Resonz.ar(windNoise, archF, 0.02) * (1 / (i + 1))
    });
    archSig = archSig * arch * 0.5 * sighMod;

    // === WHISPER (breathy voices) ===
    whisperSig = PinkNoise.ar;
    // Multiple formant-like bands
    whisperSig = BPF.ar(whisperSig, 400 * LFNoise2.kr(0.3).range(0.8, 1.2), 0.1) * 2;
    whisperSig = whisperSig + (BPF.ar(PinkNoise.ar, 2000, 0.2) * 0.5);
    whisperSig = whisperSig * LFNoise1.kr(3 + (whisper * 5)).range(0, 1);  // Choppy
    whisperSig = whisperSig * whisper * 0.3;

    // === DUST (particles) ===
    dustSig = Dust.ar(dust * 100) * 0.3;
    dustSig = dustSig + (Crackle.ar(1.5 + (dust * 0.3)) * dust * 0.1);
    dustSig = HPF.ar(dustSig, 2000);
    dustSig = dustSig * dust;

    // === MIX ===
    sig = windSig + archSig + whisperSig + dustSig;

    // Spatial depth
    sig = sig + (CombL.ar(sig, 0.3, 0.13, 1.5) * 0.2);
    sig = sig + (CombL.ar(sig, 0.3, 0.21, 1.2) * 0.15);

    sig = sig.tanh;

    sig = ~stereoSpread.(sig, 0.5, 0.3);  // Wide stereo
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] forgottenbreath loaded".postln;
