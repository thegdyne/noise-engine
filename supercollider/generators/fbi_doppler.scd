/*
FBI Doppler Generator
Passing emergency vehicle with doppler effect

Signal flow: Siren → Doppler shift → Stereo pan → Filter → ENV VCA → Output

Custom params:
  - P1 pass_speed: 0-1 (how fast vehicle passes)
  - P2 distance: 0-1 (closest approach distance)
  - P3 tone_split: 0-1 (siren interval)
  - P4 switch_rate: 0-1 (siren alternation)
  - P5 echo: 0-1 (environmental reflection)
*/

SynthDef(\fbiDoppler, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                         filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                         midiTrigBus=0, slotIndex=0,
                         customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var passSpeed, distance, toneSplit, switchRate, echo;
    var position, doppler, freqLo, freqHi, currentFreq, switcher, distanceAmp;
    
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
    passSpeed = In.kr(customBus0);
    distance = In.kr(customBus1);
    toneSplit = In.kr(customBus2);
    switchRate = In.kr(customBus3);
    echo = In.kr(customBus4);
    
    // === SOUND SOURCE ===
    position = LFSaw.kr(passSpeed.linexp(0, 1, 0.05, 1)).range(-1, 1);
    doppler = position.linlin(-1, 1, 1.1, 0.9);
    distanceAmp = (1 - position.abs) * distance.linlin(0, 1, 0.5, 1);
    
    freqLo = freq * doppler;
    freqHi = freq * toneSplit.linexp(0, 1, 1.1, 2.0) * doppler;
    
    switcher = LFPulse.kr(switchRate.linexp(0, 1, 0.5, 8));
    currentFreq = SelectX.kr(switcher, [freqLo, freqHi]);
    
    sig = SinOsc.ar(currentFreq) * distanceAmp * 0.5;
    sig = sig + (CombC.ar(sig, 0.3, echo.linlin(0, 1, 0.05, 0.2), echo * 2) * echo * 0.3);
    
    // === PROCESSING CHAIN ===
    sig = sig ! 2;  // Dual mono for channel strip panning
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    
    Out.ar(out, sig);
}).add;

"  ✓ fbiDoppler loaded".postln;
