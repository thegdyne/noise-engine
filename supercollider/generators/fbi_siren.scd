/*
FBI Siren Generator
Classic two-tone emergency siren

Signal flow: Dual oscillators → Alternation → Filter → ENV VCA → Output

Custom params:
  - P1 tone_split: 0-1 (interval between tones)
  - P2 switch_rate: 0-1 (alternation speed)
  - P3 waveform: 0-1 (sine <-> square)
  - P4 portamento: 0-1 (glide between tones)
  - P5 warble: 0-1 (vibrato depth)
*/

SynthDef(\fbiSiren, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                       filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                       midiTrigBus=0, slotIndex=0,
                       customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var toneSplit, switchRate, waveform, portamento, warble;
    var freqLo, freqHi, currentFreq, switcher, vibrato;
    
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
    toneSplit = In.kr(customBus0);
    switchRate = In.kr(customBus1);
    waveform = In.kr(customBus2);
    portamento = In.kr(customBus3);
    warble = In.kr(customBus4);
    
    // === SOUND SOURCE ===
    freqLo = freq;
    freqHi = freq * toneSplit.linexp(0, 1, 1.1, 2.0);
    
    switcher = LFPulse.kr(switchRate.linexp(0, 1, 0.5, 8));
    currentFreq = SelectX.kr(switcher, [freqLo, freqHi]);
    currentFreq = currentFreq.lag(portamento.linexp(0, 1, 0.001, 0.3));
    
    vibrato = SinOsc.kr(5 + (switchRate * 3)) * warble * currentFreq * 0.02;
    currentFreq = currentFreq + vibrato;
    
    sig = SelectX.ar(waveform, [
        SinOsc.ar(currentFreq),
        Pulse.ar(currentFreq, 0.5)
    ]) * 0.5;
    
    // === PROCESSING CHAIN ===
    sig = sig ! 2;  // Dual mono for channel strip panning
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    
    Out.ar(out, sig);
}).add;

"  ✓ fbiSiren loaded".postln;
