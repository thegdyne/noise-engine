/*
C64 SID Generator
Emulates the Commodore 64 SID chip characteristics

Features:
  - Classic SID waveforms (tri/saw/pulse/noise)
  - PWM with modulatable pulse width
  - Ring modulation (SID voice interaction style)
  - Hard sync between oscillators
  - Bit reduction for that 8-bit crunch

Custom params:
  - P1 pwm_width: Pulse width for square wave (0.05-0.95)
  - P2 waveform: 0=tri, 1=saw, 2=pulse, 3=noise
  - P3 ring_mod: Ring modulation depth
  - P4 hard_sync: Sync oscillator ratio
  - P5 bit_crush: Bit depth reduction (4-12 bits)
*/

SynthDef(\c64_sid, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                      filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                      midiTrigBus=0, slotIndex=0,
                      customBus0, customBus1, customBus2, customBus3, customBus4, portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var pwmWidth, waveform, ringMod, hardSync, bitCrush;
    var tri, saw, pulse, noise, syncOsc, modOsc;
    var bitDepth, bitMult;
    
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
    pwmWidth = In.kr(customBus0);
    waveform = In.kr(customBus1);
    ringMod = In.kr(customBus2);
    hardSync = In.kr(customBus3);
    bitCrush = In.kr(customBus4);
    
    // === OSCILLATORS ===
    // Sync oscillator (master)
    syncOsc = LFSaw.ar(freq);
    
    // Main oscillators with hard sync option
    tri = LFTri.ar(freq * hardSync);
    saw = LFSaw.ar(freq * hardSync);
    pulse = Pulse.ar(freq * hardSync, pwmWidth);
    
    // SID-style digital noise (LFSR character)
    noise = LFNoise0.ar(freq * 8).round(0.125);
    
    // Waveform select
    sig = SelectX.ar(waveform, [tri, saw, pulse, noise]);
    
    // Ring modulation (SID voice 3 style)
    modOsc = SinOsc.ar(freq * 0.5);
    sig = XFade2.ar(sig, sig * modOsc, ringMod.linlin(0, 1, -1, 1));
    
    // === BIT REDUCTION (SID character) ===
    bitDepth = bitCrush.round(1);
    bitMult = 2.pow(bitDepth - 1);
    sig = (sig * bitMult).round / bitMult;
    
    // === PROCESSING CHAIN ===
    sig = ~stereoSpread.(sig, 0.2, 0.2);  // rate=0.2, width=0.2
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  [x] c64_sid loaded".postln;
