/*
Granular Generator
Micro-sample cloud synthesis using sine grains

Signal flow: Grain Triggers → Grain Synthesis → Filter → ENV VCA → Output

Custom params:
  - P1 pitch_shift: -24 to +24 semitones
  - P2 grain_size: 0.01-0.5s (grain duration)
  - P3 grain_density: 1-100 grains/sec
  - P4 position_jitter: 0-1 (pitch/time randomness)
  - P5 stereo_spread: 0-1 (pan width)
*/

SynthDef(\granular, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                       filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                       midiTrigBus=0, slotIndex=0,
                       customBus0, customBus1, customBus2, customBus3, customBus4, portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var pitchShift, grainSize, density, jitter, spread;
    var grainTrig, grainFreq, grainDur, pan;
    
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
    pitchShift = In.kr(customBus0);
    grainSize = In.kr(customBus1);
    density = In.kr(customBus2);
    jitter = In.kr(customBus3);
    spread = In.kr(customBus4);
    
    // === SOUND SOURCE ===
    grainTrig = Impulse.ar(density);
    grainFreq = freq * (2 ** (pitchShift / 12));
    grainFreq = grainFreq * (1 + (TRand.ar(-1, 1, grainTrig) * jitter * 0.2));
    grainFreq = grainFreq.clip(20, 20000);
    
    grainDur = grainSize * (1 + (TRand.ar(-0.5, 0.5, grainTrig) * jitter));
    grainDur = grainDur.clip(0.005, 0.5);
    
    pan = TRand.ar(-1, 1, grainTrig) * spread;
    
    sig = GrainSin.ar(
        numChannels: 2,
        trigger: grainTrig,
        dur: grainDur,
        freq: grainFreq,
        pan: pan,
        mul: 0.3
    );
    
    sig = sig + GrainSin.ar(
        numChannels: 2,
        trigger: Dust.ar(density * 0.3),
        dur: grainDur * 0.5,
        freq: grainFreq * TRand.ar(0.99, 1.01, grainTrig),
        pan: TRand.ar(-1, 1, Dust.ar(density * 0.3)) * spread,
        mul: 0.1
    );
    
    // === PROCESSING CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);  // SSOT: per-slot generator bus is 2ch
    Out.ar(out, sig);
}).add;

"  ✓ granular loaded".postln;
