/*
PT2399 Grainy Generator
Bandpass-filtered noise through lo-fi delay - the "musical" version

Signal flow: Noise → Bandpass(FRQ) → Delay → Light Degradation → Filter → ENV VCA → Output

Custom params:
  - P1 delay_time: 0.001-0.5 s (short = comb, long = echo)
  - P2 feedback: 0.0-0.85 (stays stable)
  - P3 bandwidth: 0.01-1.0 (narrow = tonal, wide = noisy)
  - P4 tone: 0.0-1.0 (dark <-> bright delay character)
  - P5 grit: 0.0-1.0 (clean <-> lo-fi)
*/

SynthDef(\pt2399Grainy, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                          filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                          midiTrigBus=0, slotIndex=0,
                          customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, source, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var delayTime, feedback, bandwidth, tone, grit;
    var delayed, dry, fbSig, panPos, pitchWobble, degraded;
    
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
    delayTime = In.kr(customBus0);
    feedback = In.kr(customBus1);
    bandwidth = In.kr(customBus2);
    tone = In.kr(customBus3);
    grit = In.kr(customBus4);
    
    // === SOUND SOURCE ===
    source = WhiteNoise.ar(0.8);
    source = BPF.ar(source, freq.clip(20, 16000), bandwidth.linexp(0.01, 1, 0.01, 0.5)) * 4;
    
    dry = source ! 2;  // Dual mono for channel strip panning
    
    fbSig = LocalIn.ar(2);
    pitchWobble = LFNoise1.kr(2).range(0.998, 1.002);
    delayed = DelayC.ar(dry + (fbSig * feedback), 0.6, delayTime * pitchWobble);
    
    delayed = SelectX.ar(tone, [
        LPF.ar(delayed, 2000),
        delayed,
        HPF.ar(delayed, 500)
    ]);
    
    degraded = delayed.round(grit.linexp(0, 1, 0.0001, 0.1));
    degraded = degraded + (PinkNoise.ar * grit * 0.05);
    
    LocalOut.ar(degraded);
    
    sig = dry + degraded;
    
    // === PROCESSING CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    
    Out.ar(out, sig);
}).add;

"  ✓ pt2399Grainy loaded".postln;
