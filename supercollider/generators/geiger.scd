/*
Geiger Counter Generator
Radioactive click generator with Poisson distribution

Signal flow: Click generation → Filter → ENV VCA → Output

Custom params:
  - P1 count_rate: 0.1-100 Hz (clicks/sec, Poisson)
  - P2 dead_time: 0-1 (tube recovery, click clustering)
  - P3 click_brightness: 0-1 (soft thud <-> sharp crack)
  - P4 click_decay: 0.01-1 (tube/speaker resonance)
  - P5 background_noise: 0-1 (tube hiss/crackle)
*/

SynthDef(\geiger, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                     filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                     midiTrigBus=0, slotIndex=0,
                     customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, click, noise, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var countRate, deadTime, clickBrightness, clickDecay, backgroundNoise;
    var clickTrig, effectiveRate;
    
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
    countRate = In.kr(customBus0);
    deadTime = In.kr(customBus1);
    clickBrightness = In.kr(customBus2);
    clickDecay = In.kr(customBus3);
    backgroundNoise = In.kr(customBus4);
    
    // === SOUND SOURCE ===
    effectiveRate = countRate / (1 + (deadTime * countRate * 0.1));
    clickTrig = Dust.ar(effectiveRate);
    
    click = EnvGen.ar(
        Env.perc(0.0001, clickDecay.linexp(0.01, 1, 0.005, 0.05)),
        clickTrig
    ) * WhiteNoise.ar;
    
    click = BPF.ar(click, freq.clip(20, 16000), 0.1) * 8;
    click = click + (HPF.ar(click, clickBrightness.linexp(0.001, 1, 200, 8000)) * clickBrightness * 2);
    
    noise = PinkNoise.ar * backgroundNoise * 0.5;
    noise = noise + (Dust.ar(countRate * 10) * 0.1 * backgroundNoise);
    
    sig = click + noise;
    sig = ~ensure2ch.(sig);  // SSOT: per-slot generator bus is 2ch
    
    // === PROCESSING CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    
    Out.ar(out, sig);
}).add;

"  ✓ geiger loaded".postln;
