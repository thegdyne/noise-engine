/*
Pulse Bass Generator (Example Pack)
Classic pulse wave bass with PWM and sub oscillator

Custom params:
  - P1 pulse_width: 0.1-0.9 (pulse width)
  - P2 pwm_depth: 0-1 (PWM modulation depth)
  - P3 pwm_rate: 0.1-10 Hz (PWM rate, exp scaled)
  - P4 sub_level: 0-1 (sub oscillator level)
*/

SynthDef(\example_pulse_bass, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4, portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var pulseWidth, pwmDepth, pwmRate, subLevel;
    var pwmLfo, modWidth, pulse, sub;
    
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
    
    // Custom params (pwm_rate is exp scaled 0.1-10 Hz in JSON)
    pulseWidth = In.kr(customBus0);
    pwmDepth = In.kr(customBus1);
    pwmRate = In.kr(customBus2).linexp(0, 1, 0.1, 10);
    subLevel = In.kr(customBus3);
    
    // === SOUND SOURCE ===
    pwmLfo = SinOsc.kr(pwmRate);
    modWidth = pulseWidth + (pwmLfo * pwmDepth * 0.3);
    modWidth = modWidth.clip(0.1, 0.9);
    
    pulse = Pulse.ar(freq, modWidth);
    sub = SinOsc.ar(freq * 0.5) * subLevel;
    
    sig = (pulse * 0.7) + sub;
    
    // === PROCESSING CHAIN ===
    sig = ~stereoSpread.(sig, 0.2, 0.1);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  [x] example_pulse_bass loaded".postln;
