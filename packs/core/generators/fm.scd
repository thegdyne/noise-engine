/*
FM Generator
Frequency modulation synthesis with multiple algorithms

Signal flow: Operators -> Algorithm -> Filter -> ENV VCA -> Output

Custom params:
  - P1 ratio: 0.5-8.0 (modulator:carrier ratio)
  - P2 index: 0-20 (modulation depth)
  - P3 index_env: 0-1 (index envelope amount - decay)
  - P4 algorithm: 0-7 discrete (operator routing)
  - P5 feedback: 0-1 (operator self-feedback)
*/

SynthDef(\fm, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                 filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                 midiTrigBus=0, slotIndex=0,
                 customBus0, customBus1, customBus2, customBus3, customBus4, portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var ratio, index, indexEnv, algorithm, feedback;
    var modFreq, car, mod1, mod2, fb, indexMod;
    
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
    ratio = In.kr(customBus0);
    index = In.kr(customBus1);
    indexEnv = In.kr(customBus2);
    algorithm = In.kr(customBus3);
    feedback = In.kr(customBus4);
    
    // === SOUND SOURCE ===
    modFreq = freq * ratio;
    indexMod = index * (1 - (indexEnv * 0.8));
    
    fb = LocalIn.ar(1) * feedback * 2pi;
    mod1 = SinOsc.ar(modFreq + fb, mul: indexMod * modFreq);
    LocalOut.ar(mod1 / (indexMod * modFreq + 0.001));
    
    mod2 = SinOsc.ar(modFreq * 2, mul: indexMod * 0.5 * modFreq);
    
    // Simple algorithm selection
    sig = SelectX.ar(algorithm.min(3), [
        SinOsc.ar(freq + mod1),
        SinOsc.ar(freq + mod1 + mod2),
        SinOsc.ar(freq + (mod1 * mod2 / (modFreq + 1))),
        SinOsc.ar(freq) + (SinOsc.ar(freq * 2 + mod1) * 0.5)
    ]) * 0.5;
    
    // === PROCESSING CHAIN ===
    sig = ~ensure2ch.(sig);  // SSOT: per-slot generator bus is 2ch
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    
    Out.ar(out, sig);
}).add;

"  [x] fm loaded".postln;
