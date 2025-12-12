/*
Diode Ring Generator
Classic diode ring modulator

Signal flow: Carrier × Modulator → Diode nonlinearity → Filter → ENV VCA → Output

Custom params:
  - P1 mod_ratio: 0.1-10 (modulator frequency ratio)
  - P2 mod_depth: 0-1 (modulation amount)
  - P3 diode_curve: 0-1 (soft <-> hard clipping)
  - P4 carrier_wave: 0-1 (sine <-> saw)
  - P5 mod_wave: 0-1 (sine <-> square)
*/

SynthDef(\diodeRing, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                        filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                        midiTrigBus=0, slotIndex=0,
                        customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var modRatio, modDepth, diodeCurve, carrierWave, modWave;
    var carrier, modulator, modFreq;
    
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
    modDepth = In.kr(customBus1);
    diodeCurve = In.kr(customBus2);
    carrierWave = In.kr(customBus3);
    modWave = In.kr(customBus4);
    
    // === SOUND SOURCE ===
    modFreq = freq * modRatio;
    
    carrier = SelectX.ar(carrierWave, [
        SinOsc.ar(freq),
        Saw.ar(freq)
    ]);
    
    modulator = SelectX.ar(modWave, [
        SinOsc.ar(modFreq),
        Pulse.ar(modFreq, 0.5)
    ]);
    
    sig = carrier * ((modulator * modDepth) + (1 - modDepth));
    sig = (sig * diodeCurve.linexp(0, 1, 1, 8)).tanh * diodeCurve.linlin(0, 1, 1, 0.5);
    sig = sig + (carrier * (1 - modDepth) * 0.3);
    
    // === PROCESSING CHAIN ===
    sig = Pan2.ar(sig, LFNoise1.kr(0.3).range(-0.3, 0.3));
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    
    Out.ar(out, sig);
}).add;

"  ✓ diodeRing loaded".postln;
