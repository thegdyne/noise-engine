/*
Juno Generator
Roland Juno-60/106 inspired DCO synthesis

Features:
  - DCO-style oscillator with saw + pulse
  - Classic Juno PWM with dedicated LFO
  - Analogue drift (modulatable instability)
  - Sub oscillator (square, -1 octave)
  - Built-in Juno chorus (stereo spread)

Custom params:
  - P1 pwm_depth: PWM modulation depth
  - P2 pwm_rate: PWM LFO rate
  - P3 drift: Analogue pitch drift amount
  - P4 sub_level: Sub oscillator level
  - P5 chorus_mix: Chorus wet/dry mix
*/

SynthDef(\juno, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                   filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                   midiTrigBus=0, slotIndex=0,
                   customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var pwmDepth, pwmRate, drift, subLevel, chorusMix;
    var dcoFreq, driftLFO, pwmLFO, pulseWidth;
    var saw, pulse, sub, dry, wet;
    var chorusL, chorusR, chorusMod1, chorusMod2;
    
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
    pwmDepth = In.kr(customBus0);
    pwmRate = In.kr(customBus1);
    drift = In.kr(customBus2);
    subLevel = In.kr(customBus3);
    chorusMix = In.kr(customBus4);
    
    // === ANALOGUE DRIFT ===
    // Multiple slow LFOs for organic instability
    driftLFO = LFNoise2.kr(0.3) * drift * 0.02;  // Slow wander
    driftLFO = driftLFO + (LFNoise1.kr(2) * drift * 0.005);  // Faster jitter
    dcoFreq = freq * (1 + driftLFO);
    
    // === PWM LFO ===
    pwmLFO = SinOsc.kr(pwmRate);
    pulseWidth = pwmLFO.range(0.5 - (pwmDepth * 0.45), 0.5 + (pwmDepth * 0.45));
    
    // === DCO OSCILLATORS ===
    saw = Saw.ar(dcoFreq);
    pulse = Pulse.ar(dcoFreq, pulseWidth);
    sub = Pulse.ar(dcoFreq * 0.5, 0.5);
    
    // Mix saw and pulse (Juno has both available)
    sig = (saw * 0.5) + (pulse * 0.5) + (sub * subLevel);
    sig = sig * 0.6;  // Level balance
    
    // === JUNO CHORUS ===
    // BBD-style chorus with two slightly different rates
    chorusMod1 = SinOsc.kr(0.513) * 0.002;  // ~0.5Hz, Chorus I
    chorusMod2 = SinOsc.kr(0.863) * 0.0035; // ~0.8Hz, Chorus II
    
    dry = sig;
    chorusL = DelayC.ar(sig, 0.05, 0.005 + chorusMod1);
    chorusR = DelayC.ar(sig, 0.05, 0.005 + chorusMod2);
    
    // Stereo chorus output
    wet = [
        (dry * 0.7) + (chorusL * 0.5),
        (dry * 0.7) + (chorusR * 0.5)
    ];
    
    sig = XFade2.ar([dry, dry], wet, chorusMix.linlin(0, 1, -1, 1));
    
    // === PROCESSING CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  ✓ juno loaded".postln;
