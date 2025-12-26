/*
Buchla Generator
West Coast / Buchla-inspired synthesis

Features:
  - Complex oscillator with wavefolder
  - Variable symmetry (waveform morphing)
  - Internal modulation oscillator
  - LPG (Low-Pass Gate) with vactrol-style response
  - Chaotic modulation source

Custom params:
  - P1 timbre: Wavefolder intensity
  - P2 symmetry: Waveform symmetry (sine -> saw-like)
  - P3 modindex: Internal FM modulation depth
  - P4 lpg_decay: Low-pass gate decay time
  - P5 chaos: Chaotic modulation amount
*/

SynthDef(\buchla, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                     filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                     midiTrigBus=0, slotIndex=0,
                     customBus0, customBus1, customBus2, customBus3, customBus4, portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var timbre, symmetry, modindex, lpgDecay, chaos;
    var trig, complexOsc, modOsc, folded;
    var lpgEnv, lpgFreq, chaosLFO;
    
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
    timbre = In.kr(customBus0);
    symmetry = In.kr(customBus1);
    modindex = In.kr(customBus2);
    lpgDecay = In.kr(customBus3);
    chaos = In.kr(customBus4);
    
    // === TRIGGER ===
    trig = Select.ar(envSource, [
        DC.ar(0),
        Select.ar(clockRate.round, In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex, In.ar(midiTrigBus, 8))
    ]);
    
    // === CHAOS SOURCE ===
    chaosLFO = Crackle.ar(1.5 + (chaos * 0.4)) * chaos * 0.3;
    
    // === MODULATION OSCILLATOR ===
    modOsc = SinOsc.ar(freq * (1.5 + chaosLFO)) * modindex * freq;
    
    // === COMPLEX OSCILLATOR ===
    // Variable symmetry sine (morphs toward saw-like with asymmetry)
    complexOsc = SinOsc.ar(freq + modOsc, 0);
    
    // Add harmonics based on symmetry
    complexOsc = complexOsc + (SinOsc.ar((freq + modOsc) * 2) * symmetry * 0.3);
    complexOsc = complexOsc + (SinOsc.ar((freq + modOsc) * 3) * symmetry * 0.15);
    
    // === WAVEFOLDER ===
    // Classic Buchla-style wavefolding
    folded = complexOsc * (1 + (timbre * 8));
    folded = folded.fold(-1, 1);
    
    // Mix original and folded based on timbre
    sig = XFade2.ar(complexOsc, folded, timbre.linlin(0, 1, -1, 0.5));
    
    // === LOW-PASS GATE ===
    // Vactrol-style response: slow attack, variable decay
    // Both amplitude AND filter respond together
    lpgEnv = EnvGen.ar(
        Env.perc(0.01, lpgDecay, 1, -4),
        trig
    );
    
    // LPG filter frequency follows envelope
    lpgFreq = lpgEnv.linexp(0, 1, 100, filterFreq);
    
    // Apply LPG - filter + amplitude coupled
    sig = RLPF.ar(sig, lpgFreq, 0.5);
    sig = sig * lpgEnv;
    
    // === ADDITIONAL FILTERING ===
    // User filter on top of LPG
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    
    // === OUTPUT ===
    sig = ~stereoSpread.(sig, 0.15, 0.3);
    sig = sig * amp;
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  [x] buchla loaded".postln;
