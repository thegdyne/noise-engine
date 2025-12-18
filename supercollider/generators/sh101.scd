/*
SH-101 Generator
Roland SH-101 inspired monosynth

Features:
  - Single VCO with saw/square/both
  - Manual pulse width (no PWM LFO - use mod matrix!)
  - Sub oscillator (square, -1 oct)
  - White noise mixer
  - Classic squelchy 4-pole lowpass character
  - Filter envelope modulation

Custom params:
  - P1 waveform: 0=saw, 1=square, 2=saw+square
  - P2 pulse_width: Square wave pulse width
  - P3 sub_level: Sub oscillator level
  - P4 noise_level: Noise amount
  - P5 filter_env: Filter envelope depth
*/

SynthDef(\sh101, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                    filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                    midiTrigBus=0, slotIndex=0,
                    customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var waveform, pulseWidth, subLevel, noiseLevel, filterEnv;
    var saw, square, sub, noise, filtEnvSig;
    var envGate, envTrig, ampEnv, filtEnvGen;
    
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
    waveform = In.kr(customBus0);
    pulseWidth = In.kr(customBus1);
    subLevel = In.kr(customBus2);
    noiseLevel = In.kr(customBus3);
    filterEnv = In.kr(customBus4);
    
    // === VCO ===
    saw = Saw.ar(freq);
    square = Pulse.ar(freq, pulseWidth);
    
    sig = SelectX.ar(waveform, [
        saw,                        // 0: Saw only
        square,                     // 1: Square only
        (saw + square) * 0.6        // 2: Both mixed
    ]);
    
    // === SUB OSCILLATOR ===
    sub = Pulse.ar(freq * 0.5, 0.5);  // Square, -1 octave
    sig = sig + (sub * subLevel);
    
    // === NOISE ===
    noise = WhiteNoise.ar;
    sig = sig + (noise * noiseLevel * 0.5);
    
    // === FILTER ENVELOPE ===
    // Generate envelope for filter modulation
    // Clock triggers are audio rate, need A2K for EnvGen.kr
    envTrig = Select.ar(envSource, [
        DC.ar(0),                                    // OFF: no trigger
        Select.ar(clockRate.round, In.ar(clockTrigBus, 13)),  // CLK
        Select.ar(slotIndex, In.ar(midiTrigBus, 8))  // MIDI
    ]);
    
    filtEnvGen = EnvGen.ar(
        Env.perc(attack.max(0.001), decay.max(0.01)),
        envTrig
    );
    
    // Apply filter envelope - modulates cutoff upward
    filtEnvSig = filterFreq * (1 + (filtEnvGen * filterEnv * 4));
    
    // === FILTER (SH-101 style - resonant lowpass) ===
    // Override filter type to LP for authentic 101 sound, but respect user choice
    sig = ~multiFilter.(sig, filterType, filtEnvSig.clip(20, 16000), rq);
    
    // === OUTPUT ===
    sig = ~stereoSpread.(sig, 0.1, 0.1);  // Slight stereo
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  ✓ sh101 loaded".postln;
