/*
Sine Drone Generator (Example Pack)
Simple sine-based drone with harmonics and vibrato

Custom params:
  - P1 harmonics: 0-1 (pure sine to rich harmonics)
  - P2 detune: 0-1 (stereo detune spread)
  - P3 vibrato: 0-1 (vibrato depth)
*/

SynthDef(\example_sine_drone, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var harmonics, detune, vibrato;
    var vibLfo, freqL, freqR, sig1, sig2, sig3;
    
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
    harmonics = In.kr(customBus0);
    detune = In.kr(customBus1);
    vibrato = In.kr(customBus2);
    
    // === SOUND SOURCE ===
    vibLfo = SinOsc.kr(5) * vibrato * 0.02;
    freqL = freq * (1 + vibLfo) * (1 - (detune * 0.01));
    freqR = freq * (1 + vibLfo) * (1 + (detune * 0.01));
    
    // Fundamental + harmonics blend
    sig1 = SinOsc.ar([freqL, freqR]);
    sig2 = SinOsc.ar([freqL, freqR] * 2) * 0.5;
    sig3 = SinOsc.ar([freqL, freqR] * 3) * 0.25;
    
    sig = sig1 + ((sig2 + sig3) * harmonics);
    sig = sig * 0.5;  // Normalize
    
    // === PROCESSING CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  ✓ example_sine_drone loaded".postln;
