/*
TEMPEST Generator
Storm and churning sea - nature's fury

Features:
  - Crashing waves
  - Howling wind
  - Thunder rumble
  - Sea spray and foam
  - Storm surge

Custom params:
  - P1 waves: Wave crash intensity
  - P2 wind: Wind howling level
  - P3 thunder: Thunder rumble
  - P4 spray: High frequency spray/foam
  - P5 surge: Overall storm intensity

Primarily continuous with triggered thunder/wave crashes.
*/

SynthDef(\tempest, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                      filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                      midiTrigBus=0, slotIndex=0,
                      customBus0, customBus1, customBus2, customBus3, customBus4|
    
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var waves, wind, thunder, spray, surge;
    var trig, surgeMod;
    var wavesSig, windSig, thunderSig, spraySig;
    var waveNoise, waveLFO, waveCrash;
    var windNoise, windMod;
    var thunderOsc, thunderEnv;
    var sprayNoise;
    
    // Standard params
    freq = In.kr(freqBus);
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);
    
    // Custom params
    waves = In.kr(customBus0);
    waves = Lag.kr(waves, 0.05);
    wind = In.kr(customBus1);
    wind = Lag.kr(wind, 0.05);
    thunder = In.kr(customBus2);
    spray = In.kr(customBus3);
    spray = Lag.kr(spray, 0.05);
    surge = In.kr(customBus4);
    surge = Lag.kr(surge, 0.1);
    
    // === TRIGGER ===
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);
    
    // Surge modulates everything
    surgeMod = surge * 0.5 + 0.5;  // 0.5 to 1.0 range
    
    // === WAVES (crashing) ===
    // Filtered noise with slow amplitude envelope
    waveNoise = BrownNoise.ar + (WhiteNoise.ar * 0.3);
    waveLFO = LFNoise2.kr(0.15 + (surge * 0.2)).range(0, 1);  // Slow wave cycle
    // Shape like wave: build, crash, retreat
    waveLFO = (waveLFO ** 0.5) * (1 - (waveLFO ** 3));  // Asymmetric shape
    wavesSig = BPF.ar(waveNoise, 200 + (waveLFO * 400), 0.6);
    wavesSig = wavesSig + (LPF.ar(waveNoise, 100) * waveLFO * 0.5);  // Low rumble
    // Triggered crashes
    waveCrash = EnvGen.ar(Env.perc(0.05, 1.5 * surgeMod, 1, -4), trig);
    wavesSig = wavesSig + (BPF.ar(waveNoise, 300, 0.4) * waveCrash * 2);
    wavesSig = wavesSig * waves * surgeMod;
    
    // === WIND (howling) ===
    // Resonant filtered noise
    windNoise = PinkNoise.ar;
    windMod = LFNoise2.kr(0.3 + (surge * 0.5)).range(0.7, 1.3);
    // Multiple resonant peaks for howling
    windSig = BPF.ar(windNoise, 400 * windMod * surgeMod, 0.1) * 2;
    windSig = windSig + (BPF.ar(windNoise, 800 * windMod, 0.15) * 1.5);
    windSig = windSig + (BPF.ar(windNoise, 1600 * windMod, 0.2));
    // Gusts
    windSig = windSig * LFNoise2.kr(1 + (surge * 2)).range(0.4, 1);
    windSig = windSig * wind * surgeMod * 0.5;
    
    // === THUNDER (rumble) ===
    // Low frequency impact with long tail
    thunderEnv = EnvGen.ar(
        Env.perc(0.01, 3 * surgeMod, 1, -4),
        trig + Dust.ar(thunder * 0.3 * surge)  // Clock + random
    );
    thunderOsc = BrownNoise.ar;
    thunderOsc = LPF.ar(thunderOsc, 80 + (thunderEnv * 200));
    // Add pitched rumble
    thunderOsc = thunderOsc + (SinOsc.ar(freq * 0.25 * LFNoise2.kr(2).range(0.9, 1.1)) * 0.4);
    // Distance variation
    thunderOsc = LPF.ar(thunderOsc, 200 + (thunder * 600));
    thunderSig = thunderOsc * thunderEnv * thunder;
    
    // === SPRAY (foam and mist) ===
    // High frequency noise
    sprayNoise = WhiteNoise.ar;
    spraySig = HPF.ar(sprayNoise, 2000 + (surge * 2000));
    spraySig = spraySig + (BPF.ar(sprayNoise, 4000, 0.5) * 0.5);
    // Triggered on wave crashes
    spraySig = spraySig * (
        LFNoise2.kr(2).range(0.3, 1) +
        (EnvGen.ar(Env.perc(0.01, 0.5), trig) * 0.5)
    );
    spraySig = spraySig * spray * surgeMod * 0.3;
    
    // === MIX ===
    sig = wavesSig + windSig + thunderSig + spraySig;
    
    // Soft limiting
    sig = sig.tanh;
    
    // === PROCESSING CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~stereoSpread.(sig, 0.25, 0.3);  // Wide chaotic movement
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  ✓ tempest loaded".postln;
