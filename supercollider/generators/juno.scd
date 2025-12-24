/*
Juno Generator
Roland Juno-60/106 inspired DCO synthesis

Features:
  - DCO-style oscillator with saw + pulse
  - Classic Juno PWM with dedicated LFO
  - Analogue drift (modulatable instability)
  - Sub oscillator (square, -1 octave)
  - Built-in Juno chorus (post-VCA, stereo spread)

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
                   customBus0, customBus1, customBus2, customBus3, customBus4, portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var pwmDepth, pwmRate, drift, subLevel, chorusMix;
    var dcoFreq, driftLFO, driftAmount, pwmLFO, pulseWidth;
    var saw, pulse, sub, dry, wet;
    var chorusL, chorusR, chorusMod1, chorusMod2;
    
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
    
    // Custom params with smoothing
    pwmDepth = In.kr(customBus0);
    pwmDepth = Lag.kr(pwmDepth, 0.02);
    pwmRate = In.kr(customBus1);
    pwmRate = Lag.kr(pwmRate, 0.02);
    drift = In.kr(customBus2);
    drift = Lag.kr(drift, 0.05);
    subLevel = In.kr(customBus3);
    subLevel = Lag.kr(subLevel, 0.02);
    chorusMix = In.kr(customBus4);
    chorusMix = Lag.kr(chorusMix, 0.02);
    
    // === ANALOGUE DRIFT ===
    // Multiple slow LFOs for organic instability
    // Squared mapping: first half subtle, last quarter wild
    driftAmount = drift.squared;
    driftLFO = LFNoise2.kr(0.3) * driftAmount * 0.02;  // Slow wander
    driftLFO = driftLFO + (LFNoise1.kr(2) * driftAmount * 0.005);  // Faster jitter
    dcoFreq = freq * (1 + driftLFO);
    
    // === PWM LFO ===
    pwmLFO = SinOsc.kr(pwmRate);
    pulseWidth = pwmLFO.range(0.5 - (pwmDepth * 0.45), 0.5 + (pwmDepth * 0.45));
    pulseWidth = pulseWidth.clip(0.05, 0.95);  // Safety clamp for modulation edge cases
    
    // === DCO OSCILLATORS ===
    saw = Saw.ar(dcoFreq);
    pulse = Pulse.ar(dcoFreq, pulseWidth);
    sub = Pulse.ar(dcoFreq * 0.5, 0.5);
    
    // Mix saw and pulse (Juno has both available)
    // Slight gain compensation when sub is high
    sig = (saw * 0.5) + (pulse * 0.5) + (sub * subLevel);
    sig = sig * (0.6 - (subLevel * 0.1));  // Level balance with sub compensation
    
    // === PROCESSING CHAIN (filter + VCA first) ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    
    // === JUNO CHORUS (post-filter, post-VCA for authentic behaviour) ===
    // HPF before chorus to tighten low end (authentic Juno)
    sig = HPF.ar(sig, 120);
    
    // BBD-style chorus with two slightly different rates
    // Increased depth for more pronounced movement
    chorusMod1 = SinOsc.kr(0.513) * 0.003;  // ~0.5Hz, Chorus I
    chorusMod2 = SinOsc.kr(0.863) * 0.005;  // ~0.8Hz, Chorus II
    
    dry = sig;
    chorusL = DelayC.ar(sig, 0.05, 0.005 + chorusMod1);
    chorusR = DelayC.ar(sig, 0.05, 0.005 + chorusMod2);
    
    // Stereo chorus output
    wet = [
        (dry * 0.7) + (chorusL * 0.5),
        (dry * 0.7) + (chorusR * 0.5)
    ];
    
    sig = XFade2.ar([dry, dry], wet, chorusMix.linlin(0, 1, -1, 1));
    
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  ✓ juno loaded".postln;
