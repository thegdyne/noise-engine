/*
Granular Generator
Micro-sample cloud synthesis using sine grains

Signal flow: P1-P5 → Grain Triggers → Grain Synthesis → Filter → ENVELOPE → Output

Standard params:
  - frequency: grain center pitch (20-8000 Hz)
  - cutoff: 1-16000 Hz
  - resonance: 0.001-1.0
  - attack/decay: final VCA envelope

Custom params:
  - custom[0] pitch_shift: -24 to +24 semitones
  - custom[1] grain_size: 0.01-0.5s (grain duration)
  - custom[2] grain_density: 1-100 grains/sec
  - custom[3] position_jitter: 0-1 (pitch/time randomness)
  - custom[4] stereo_spread: 0-1 (pan width)

ENV OFF = continuous grain cloud
ENV ON = clock-synced envelope gates final output
*/

SynthDef(\granular, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                       filterTypeBus, envEnabledBus, clockRateBus, clockTrigBus,
                       customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, env, freq, filterFreq, rq, filterType, attack, decay, amp;
    var envEnabled, clockRate, allTrigs, clockTrig;
    var pitchShift, grainSize, density, jitter, spread;
    var trig, grainFreq, grainDur, pan;
    
    // Read standard params
    freq = In.kr(freqBus);
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envEnabled = In.kr(envEnabledBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);
    
    // Read custom params
    pitchShift = In.kr(customBus0);   // -24 to +24 semitones
    grainSize = In.kr(customBus1);    // 0.01-0.5s
    density = In.kr(customBus2);      // 1-100 grains/sec
    jitter = In.kr(customBus3);       // 0-1
    spread = In.kr(customBus4);       // 0-1
    
    // === SOUND SOURCE (runs continuously) ===
    
    // Grain trigger with variable density
    trig = Impulse.ar(density);
    
    // Grain frequency with pitch shift and jitter
    grainFreq = freq * (2 ** (pitchShift / 12));
    grainFreq = grainFreq * (1 + (TRand.ar(-1, 1, trig) * jitter * 0.2));
    grainFreq = grainFreq.clip(20, 20000);
    
    // Grain duration with jitter
    grainDur = grainSize * (1 + (TRand.ar(-0.5, 0.5, trig) * jitter));
    grainDur = grainDur.clip(0.005, 0.5);
    
    // Stereo pan per grain
    pan = TRand.ar(-1, 1, trig) * spread;
    
    // Main grain synthesis using GrainSin
    sig = GrainSin.ar(
        numChannels: 2,
        trigger: trig,
        dur: grainDur,
        freq: grainFreq,
        pan: pan,
        mul: 0.3
    );
    
    // Add texture layer with noise grains at related frequency
    sig = sig + GrainSin.ar(
        numChannels: 2,
        trigger: Dust.ar(density * 0.3),
        dur: grainDur * 0.5,
        freq: grainFreq * TRand.ar(0.99, 1.01, trig),
        pan: TRand.ar(-1, 1, Dust.ar(density * 0.3)) * spread,
        mul: 0.1
    );
    
    // Add subtle noise texture (simpler than GrainBuf)
    sig = sig + (PinkNoise.ar * EnvGen.ar(Env.perc(0.001, grainDur), Dust.ar(density * 0.2)) * 0.05 * jitter);
    
    // === FILTER ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    
    // === ENVELOPE AS FINAL VCA ===
    allTrigs = In.ar(clockTrigBus, 12);
    clockTrig = Select.ar(clockRate, allTrigs);
    
    env = EnvGen.ar(Env.perc(attack, decay), clockTrig);
    sig = Select.ar(envEnabled, [sig, sig * env]);
    
    sig = sig * amp;
    
    Out.ar(out, sig);
}).add;

"  ✓ granular loaded".postln;
