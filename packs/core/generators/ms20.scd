/*
MS-20 Generator
Korg MS-20 inspired semi-modular synth

Features:
  - Two oscillators (saw + pulse)
  - Ring modulator
  - Aggressive Korg-style filter with drive
  - High-pass filter (MS-20 has both HP and LP)
  - Pink/white noise mixer

Custom params:
  - P1 osc_mix: OSC1 (saw) / OSC2 (pulse) balance
  - P2 ring: Ring modulation amount
  - P3 filter_drive: Pre-filter saturation (Korg character)
  - P4 hpf: High-pass filter frequency
  - P5 noise: Noise level
*/

SynthDef(\ms20, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                   filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                   midiTrigBus=0, slotIndex=0,
                   customBus0, customBus1, customBus2, customBus3, customBus4, portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var oscMix, ring, filterDrive, hpfAmt, noiseLevel;
    var osc1, osc2, ringMod, noise;
    var hpfFreq, filtered;
    
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
    oscMix = In.kr(customBus0);
    ring = In.kr(customBus1);
    filterDrive = In.kr(customBus2);
    hpfAmt = In.kr(customBus3);
    noiseLevel = In.kr(customBus4);
    
    // === OSCILLATORS ===
    // OSC1: Sawtooth
    osc1 = Saw.ar(freq);
    
    // OSC2: Pulse with slight detune
    osc2 = Pulse.ar(freq * 1.002, 0.5);
    
    // Mix oscillators
    sig = (osc1 * (1 - oscMix)) + (osc2 * oscMix);
    
    // === RING MODULATOR ===
    ringMod = osc1 * osc2;
    sig = XFade2.ar(sig, ringMod, ring.linlin(0, 1, -1, 1));
    
    // === NOISE ===
    noise = PinkNoise.ar;
    sig = sig + (noise * noiseLevel * 0.5);
    
    // === MS-20 FILTER CHARACTER ===
    // Pre-filter drive (this is key to the MS-20 sound)
    sig = (sig * (1 + (filterDrive * 4))).tanh;
    
    // High-pass filter (MS-20 has HP before LP)
    hpfFreq = hpfAmt.linexp(0, 1, 20, 2000);
    sig = HPF.ar(sig, hpfFreq);
    
    // Low-pass filter with aggressive resonance
    // MS-20 filter self-oscillates and screams at high res
    // Using MoogFF for that aggressive character
    filtered = MoogFF.ar(sig, filterFreq, rq.linlin(0.1, 1.0, 3.5, 0) * 0.95);
    
    // Blend based on filter type (LP/HP/BP modes)
    sig = Select.ar(filterType, [
        filtered,  // LP
        HPF.ar(sig, filterFreq),  // HP
        BPF.ar(sig, filterFreq, rq, 2)  // BP
    ]);
    
    // === OUTPUT ===
    sig = ~stereoSpread.(sig, 0.1, 0.2);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  [x] ms20 loaded".postln;
