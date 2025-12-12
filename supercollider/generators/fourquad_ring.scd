/*
Four-Quadrant Ring Generator
Balanced four-quadrant multiplier ring modulator

Signal flow: Carrier × Modulator (balanced) → Filter → ENV VCA → Output

Custom params:
  - P1 mod_ratio: 0.1-10 (modulator frequency ratio)
  - P2 balance: 0-1 (carrier bleed amount)
  - P3 symmetry: 0-1 (quadrant balance)
  - P4 carrier_wave: 0-1 (sine <-> triangle)
  - P5 mod_wave: 0-1 (sine <-> triangle)
*/

SynthDef(\fourQuadRing, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                           filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                           midiTrigBus=0, slotIndex=0,
                           customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var modRatio, balance, symmetry, carrierWave, modWave;
    var carrier, modulator, modFreq, ring;
    
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
    modRatio = In.kr(customBus0);
    balance = In.kr(customBus1);
    symmetry = In.kr(customBus2);
    carrierWave = In.kr(customBus3);
    modWave = In.kr(customBus4);
    
    // === SOUND SOURCE ===
    modFreq = freq * modRatio;
    
    carrier = SelectX.ar(carrierWave, [
        SinOsc.ar(freq),
        LFTri.ar(freq)
    ]);
    
    modulator = SelectX.ar(modWave, [
        SinOsc.ar(modFreq),
        LFTri.ar(modFreq)
    ]);
    
    ring = carrier * modulator;
    ring = ring + (carrier * balance * 0.5);
    
    sig = (ring * symmetry.linlin(0, 1, 0.5, 1.5)).softclip;
    
    // === PROCESSING CHAIN ===
    sig = Pan2.ar(sig, LFNoise1.kr(0.2).range(-0.25, 0.25));
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    
    Out.ar(out, sig);
}).add;

"  ✓ fourQuadRing loaded".postln;
