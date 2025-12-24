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

SynthDef(\forgottenbreath, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                              filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                              midiTrigBus=0, slotIndex=0,
                              customBus0, customBus1, customBus2, customBus3, customBus4|
    
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var wind, arch, whisper, dust, sigh;
    var trig, windSig, archSig, whisperSig, dustSig, sighMod;
    var windNoise, archFreqs;
    
    // Standard params
    freq = In.kr(freqBus);
    portamento = In.kr(portamentoBus);
    freq = Lag.kr(freq, portamento.linexp(0, 1, 0.001, 0.5));
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);
    
    // Custom params
    wind = In.kr(customBus0);
    wind = Lag.kr(wind, 0.2);
    arch = In.kr(customBus1);
    arch = Lag.kr(arch, 0.1);
    whisper = In.kr(customBus2);
    whisper = Lag.kr(whisper, 0.1);
    dust = In.kr(customBus3);
    dust = Lag.kr(dust, 0.05);
    sigh = In.kr(customBus4);
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
    
    // === PROCESSING CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~stereoSpread.(sig, 0.5, 0.3);  // Wide stereo
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  ✓ forgottenbreath loaded".postln;
