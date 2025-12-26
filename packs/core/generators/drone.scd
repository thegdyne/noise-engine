/*
Drone Generator
Evolving ambient drone pad

Features:
  - Multiple detuned oscillators
  - Internal slow modulation for movement
  - Sub oscillator for depth
  - Breathy/airy noise texture
  - Perfect for Sloth modulation demonstration

Custom params:
  - P1 detune: Detuning spread between voices
  - P2 voices: Voice thickness (2-6 voices)
  - P3 movement: Internal modulation depth
  - P4 sub: Sub oscillator level
  - P5 air: Breathy texture amount
*/

SynthDef(\drone, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                    filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                    midiTrigBus=0, slotIndex=0,
                    customBus0, customBus1, customBus2, customBus3, customBus4, portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var detune, voices, movement, subLevel, air;
    var detuneAmts, voiceSigs, subOsc, airNoise;
    var moveLFO1, moveLFO2, moveLFO3;
    var numVoices;
    
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
    detune = In.kr(customBus0);
    voices = In.kr(customBus1);
    movement = In.kr(customBus2);
    subLevel = In.kr(customBus3);
    air = In.kr(customBus4);
    
    // === INTERNAL MOVEMENT LFOs ===
    moveLFO1 = LFNoise2.kr(0.1) * movement * 0.02;
    moveLFO2 = LFNoise2.kr(0.07) * movement * 0.015;
    moveLFO3 = SinOsc.kr(0.05) * movement * 0.01;
    
    // === MULTI-VOICE OSCILLATORS ===
    // Detune amounts for each voice
    detuneAmts = [-0.04, -0.02, -0.01, 0.01, 0.02, 0.04] * detune;
    
    // Generate 6 voices with varying detune and waveforms
    voiceSigs = [
        Saw.ar(freq * (1 + detuneAmts[0] + moveLFO1)),
        VarSaw.ar(freq * (1 + detuneAmts[1] + moveLFO2), width: 0.3),
        Saw.ar(freq * (1 + detuneAmts[2] - moveLFO1)),
        Pulse.ar(freq * (1 + detuneAmts[3] + moveLFO3), 0.4 + (moveLFO1 * 2)) * 0.7,
        Saw.ar(freq * (1 + detuneAmts[4] - moveLFO2)),
        VarSaw.ar(freq * (1 + detuneAmts[5] + moveLFO1), width: 0.6)
    ];
    
    // Mix voices based on voices param (fade in more voices)
    sig = (voiceSigs[0] * 0.3) + (voiceSigs[1] * 0.3);  // Always 2 voices
    sig = sig + (voiceSigs[2] * voices * 0.5);  // Add more with voices param
    sig = sig + (voiceSigs[3] * voices * 0.4);
    sig = sig + (voiceSigs[4] * (voices * 0.8).min(1) * 0.3);
    sig = sig + (voiceSigs[5] * (voices * 0.6).min(1) * 0.3);
    
    sig = sig * 0.3;  // Level balance
    
    // === SUB OSCILLATOR ===
    subOsc = SinOsc.ar(freq * 0.5) + (SinOsc.ar(freq * 0.25) * 0.5);
    sig = sig + (subOsc * subLevel * 0.4);
    
    // === AIR/BREATH TEXTURE ===
    airNoise = PinkNoise.ar;
    airNoise = BPF.ar(airNoise, freq * 3, 1.0);  // Tune to harmonic
    airNoise = airNoise + (BPF.ar(PinkNoise.ar, freq * 5, 0.5) * 0.5);
    sig = sig + (airNoise * air * 0.15);
    
    // === STEREO SPREAD ===
    sig = ~stereoSpread.(sig, 0.08, 0.5);  // Slow, wide movement
    
    // === PROCESSING CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  [x] drone loaded".postln;
