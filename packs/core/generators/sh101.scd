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
                    customBus0, customBus1, customBus2, customBus3, customBus4, portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var waveform, pulseWidth, subLevel, noiseLevel, filterEnv;
    var saw, square, sub, noise, filtEnvSig, envOctaves;
    var envTrig, filtEnvGen;
    
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
    waveform = In.kr(customBus0);
    pulseWidth = In.kr(customBus1);
    pulseWidth = pulseWidth.clip(0.05, 0.95);  // Safety clamp for modulation edge cases
    subLevel = In.kr(customBus2);
    noiseLevel = In.kr(customBus3);
    filterEnv = In.kr(customBus4);
    filterEnv = Lag.kr(filterEnv, 0.02);  // Smooth to prevent zipper noise
    
    // === VCO ===
    saw = Saw.ar(freq);
    square = Pulse.ar(freq, pulseWidth);
    
    sig = SelectX.ar(waveform, [
        saw,                        // 0: Saw only
        square,                     // 1: Square only
        (saw + square) * 0.5        // 2: Both mixed (balanced level)
    ]);
    
    // === SUB OSCILLATOR ===
    sub = Pulse.ar(freq * 0.5, 0.5);  // Square, -1 octave
    sig = sig + (sub * subLevel);
    
    // === NOISE ===
    noise = WhiteNoise.ar;
    sig = sig + (noise * noiseLevel * 0.5);
    
    // === FILTER ENVELOPE ===
    // Clock triggers are audio rate - clamp indices for safety
    envTrig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),                                                          // OFF: no trigger
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),   // CLK
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))             // MIDI
    ]);
    
    filtEnvGen = EnvGen.ar(
        Env.perc(attack.max(0.001), decay.max(0.01)),
        envTrig
    );
    
    // === FILTER MODULATION (octave-based) ===
    // Exponential scaling gives musical response across full knob range
    // Max 4 octaves of sweep
    envOctaves = filtEnvGen * filterEnv * 4;
    filtEnvSig = filterFreq * (2 ** envOctaves);
    
    // === FILTER ===
    sig = ~multiFilter.(sig, filterType, filtEnvSig.clip(20, 16000), rq);
    
    // === OUTPUT ===
    sig = ~stereoSpread.(sig, 0.1, 0.1);  // Slight stereo
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  [x] sh101 loaded".postln;
