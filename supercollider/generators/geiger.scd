/*
Geiger Counter Generator
Radioactive click generator with Poisson distribution

Signal flow: P1-P5 → Click generation → Filter → ENVELOPE → Output

Standard params:
  - frequency: click pitch (resonant frequency)
  - cutoff: 80-16000 Hz
  - resonance: 0.1-1.0
  - attack: 0.001-0.5 s (final VCA attack)
  - decay: 0.01-2.0 s (final VCA decay)

Custom params:
  - custom[0] count_rate: 0.1-100 Hz (clicks/sec, Poisson)
  - custom[1] dead_time: 0-1 (tube recovery, click clustering)
  - custom[2] click_brightness: 0-1 (soft thud <-> sharp crack)
  - custom[3] click_decay: 0.01-1 (tube/speaker resonance)
  - custom[4] background_noise: 0-1 (tube hiss/crackle)

ENV OFF = continuous clicks (drone)
ENV ON = clock-synced envelope gates final output
*/

SynthDef(\geiger, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                     filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                       midiTrigBus=0, slotIndex=0,
                     customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, click, noise, env, freq, filterFreq, rq, filterType, attack, decay, amp;
    var envSource, clockRate, allTrigs, clockTrig, allMidiTrigs, midiTrig, trig;
    var countRate, deadTime, clickBrightness, clickDecay, backgroundNoise;
    var clickTrig, effectiveRate;
    
    // Read standard params
    freq = In.kr(freqBus);
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);  // 0=OFF, 1=CLK, 2=MIDI
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);
    
    // Read custom params
    countRate = In.kr(customBus0);        // 0.1-100 Hz
    deadTime = In.kr(customBus1);         // 0-1
    clickBrightness = In.kr(customBus2);  // 0-1
    clickDecay = In.kr(customBus3);       // 0.01-1
    backgroundNoise = In.kr(customBus4);  // 0-1
    
    // === SOUND SOURCE (runs continuously) ===
    
    // Poisson-distributed triggers (Dust is already Poisson)
    // Dead time reduces effective rate at high counts (tube recovery)
    effectiveRate = countRate / (1 + (deadTime * countRate * 0.1));
    clickTrig = Dust.ar(effectiveRate);
    
    // Click transient (GM tube discharge)
    click = EnvGen.ar(
        Env.perc(0.0001, clickDecay.linexp(0.01, 1, 0.005, 0.05)),
        clickTrig
    ) * WhiteNoise.ar;
    
    // Pitched click - resonant bandpass at FRQ
    click = BPF.ar(click, freq.clip(20, 16000), 0.1) * 8;
    
    // Brightness adds highpass to let through more high harmonics
    click = click + (HPF.ar(click, clickBrightness.linexp(0.001, 1, 200, 8000)) * clickBrightness * 2);
    
    // Background tube hiss/crackle - silent at 0, loud at max
    noise = PinkNoise.ar * backgroundNoise * 0.5;
    noise = noise + (Dust.ar(countRate * 10) * 0.1 * backgroundNoise);
    
    sig = click + noise;
    
    // Stereo spread - clicks randomly panned
    sig = Pan2.ar(sig, TRand.ar(-0.5, 0.5, clickTrig));
    
    // === FILTER ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    
    // === ENVELOPE AS FINAL VCA ===
    // Clock trigger
    allTrigs = In.ar(clockTrigBus, ~clockRates.size);
    clockTrig = Select.ar(clockRate, allTrigs);
    
    // MIDI trigger - read all 8 channels and select by slotIndex
    allMidiTrigs = In.ar(midiTrigBus, 8);
    midiTrig = Select.ar(slotIndex, allMidiTrigs);
    
    // Select trigger based on envSource: 0=none, 1=clock, 2=midi
    trig = Select.ar(envSource, [
        DC.ar(0),      // 0: OFF - no triggers
        clockTrig,     // 1: CLK - clock triggers only  
        midiTrig       // 2: MIDI - midi triggers only
    ]);
    
    // Envelope
    env = EnvGen.ar(Env.perc(attack, decay), trig);
    
    // Apply envelope only when envSource > 0, otherwise drone
    sig = sig * Select.kr(envSource > 0, [1.0, env]) * amp;
    
    Out.ar(out, sig);
}).add;

"  ✓ geiger loaded".postln;
