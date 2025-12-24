/*
VCA Ring Generator
VCA-based ring modulator (softer character)

Signal flow: Carrier through VCA controlled by modulator → Filter → ENV VCA → Output

Custom params:
  - P1 mod_ratio: 0.1-10 (modulator frequency ratio)
  - P2 vca_bias: 0-1 (DC offset/carrier through)
  - P3 vca_response: 0-1 (linear <-> exponential)
  - P4 carrier_wave: 0-1 (sine <-> saw)
  - P5 lfo_mod: 0-1 (additional LFO modulation)
*/

SynthDef(\vcaRing, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                      filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                      midiTrigBus=0, slotIndex=0,
                      customBus0, customBus1, customBus2, customBus3, customBus4, portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var modRatio, vcaBias, vcaResponse, carrierWave, lfoMod;
    var carrier, modulator, modFreq, vcaControl, lfo;
    
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
    modRatio = In.kr(customBus0);
    vcaBias = In.kr(customBus1);
    vcaResponse = In.kr(customBus2);
    carrierWave = In.kr(customBus3);
    lfoMod = In.kr(customBus4);
    
    // === SOUND SOURCE ===
    modFreq = freq * modRatio;
    
    carrier = SelectX.ar(carrierWave, [
        SinOsc.ar(freq),
        Saw.ar(freq)
    ]);
    
    modulator = SinOsc.ar(modFreq).range(0, 1);
    lfo = SinOsc.kr(freq * 0.01).range(0.5, 1) * lfoMod + (1 - lfoMod);
    
    vcaControl = modulator.linexp(0, 1, vcaResponse.linlin(0, 1, 0.01, 0.5), 1);
    vcaControl = (vcaControl * (1 - vcaBias)) + vcaBias;
    vcaControl = vcaControl * lfo;
    
    sig = carrier * vcaControl * 0.7;
    
    // === PROCESSING CHAIN ===
    sig = ~ensure2ch.(sig);  // SSOT: per-slot generator bus is 2ch
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    
    Out.ar(out, sig);
}).add;

"  ✓ vcaRing loaded".postln;
