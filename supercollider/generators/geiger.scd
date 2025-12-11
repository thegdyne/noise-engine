/*
Geiger Counter Generator
Radioactive click generator with Poisson distribution

Signal flow: P1-P5 → Click generation → Filter → ENVELOPE → Output

Standard params:
  - frequency: not used
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
                     filterTypeBus, envEnabledBus, clockRateBus, clockTrigBus,
                     customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, click, noise, env, filterFreq, rq, filterType, attack, decay, amp;
    var envEnabled, clockRate, allTrigs, clockTrig;
    var countRate, deadTime, clickBrightness, clickDecay, backgroundNoise;
    var trig, effectiveRate;
    
    // Read standard params
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envEnabled = In.kr(envEnabledBus);
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
    trig = Dust.ar(effectiveRate);
    
    // Click transient (GM tube discharge)
    click = EnvGen.ar(
        Env.perc(0.0001, clickDecay.linexp(0.01, 1, 0.005, 0.05)),
        trig
    ) * WhiteNoise.ar;
    
    // Brightness = highpass filter on click (soft thud <-> sharp crack)
    click = HPF.ar(click, clickBrightness.linexp(0.001, 1, 200, 8000));
    click = click * 4;
    
    // Background tube hiss/crackle
    noise = PinkNoise.ar * backgroundNoise * 0.1;
    noise = noise + (Dust.ar(countRate * 10) * 0.02 * backgroundNoise);
    
    sig = click + noise;
    
    // Stereo spread - clicks randomly panned
    sig = Pan2.ar(sig, TRand.ar(-0.5, 0.5, trig));
    
    // === FILTER ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    
    // === ENVELOPE AS FINAL VCA ===
    // Clock trigger
    allTrigs = In.ar(clockTrigBus, 8);
    clockTrig = Select.ar(clockRate, allTrigs);
    
    // ENV OFF = pass through (continuous clicks), ENV ON = envelope gates output
    env = EnvGen.ar(Env.perc(attack, decay), clockTrig);
    sig = Select.ar(envEnabled, [sig, sig * env]);
    
    sig = sig * amp;
    
    Out.ar(out, sig);
}).add;

"  ✓ geiger loaded".postln;
