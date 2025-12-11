/*
VCA Ring Generator
OTA/Dual-VCA topology ring modulator
Based on Elektor Formant modular system (1977-1978) - C. Chapman

Signal flow: P1-P5 → Audio × CV VCAs → Filter → ENVELOPE → Output

Models VCA-based ring modulator approach:
- Uses matched OTAs (CA3080) or dual VCAs
- CV signal opens/closes audio path
- Bipolar CV creates ring mod effect
- Different topologies give different characters
- More "musical" than pure multiplication

Standard params:
  - frequency: audio oscillator pitch (20-8000 Hz)
  - cutoff: 1-16000 Hz
  - resonance: 0.001-1.0
  - attack/decay: final VCA envelope

Custom params:
  - custom[0] carrier_freq: 0.1-2000 Hz (CV/carrier frequency)
  - custom[1] audio_level: 0-1 (input headroom)
  - custom[2] cv_depth: 0-1 (modulation depth)
  - custom[3] topology: 0-2 discrete (single/dual/quad VCA)
  - custom[4] drive: 0-1 (OTA distortion character)

ENV OFF = continuous VCA ring modulation
ENV ON = clock-synced envelope gates final output
*/

SynthDef(\vcaRing, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                      filterTypeBus, envEnabledBus, clockRateBus, clockTrigBus,
                      customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, env, freq, filterFreq, rq, filterType, attack, decay, amp;
    var envEnabled, clockRate, allTrigs, clockTrig;
    var carrierFreq, audioLevel, cvDepth, topology, drive;
    var audio, cv, vcaOut, single, dual, quad;
    
    // Read standard params
    freq = In.kr(freqBus);
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envEnabled = In.kr(envEnabledBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);
    
    // Read custom params
    carrierFreq = In.kr(customBus0);   // 0.1-2000 Hz
    audioLevel = In.kr(customBus1);    // 0-1
    cvDepth = In.kr(customBus2);       // 0-1
    topology = In.kr(customBus3);      // 0-2 discrete
    drive = In.kr(customBus4);         // 0-1
    
    // === SOUND SOURCE (runs continuously) ===
    
    // Audio input (rich waveform for interesting ring mod)
    audio = Saw.ar(freq) + (Pulse.ar(freq * 1.001, 0.3) * 0.5);
    audio = audio * audioLevel;
    
    // Apply input drive (OTA input stage saturation)
    audio = (audio * (1 + (drive * 3))).tanh;
    
    // CV/Carrier signal (controls the VCA)
    cv = SinOsc.ar(carrierFreq);
    
    // === VCA TOPOLOGIES ===
    
    // Single VCA: Simple multiplication
    // CV directly controls gain (unipolar or bipolar depending on offset)
    single = audio * (cv * cvDepth + (1 - cvDepth));
    
    // Dual VCA: Matched pair for better balance
    // One VCA for positive half, one for negative
    dual = (audio * cv.max(0) * cvDepth) - (audio * cv.neg.max(0) * cvDepth);
    dual = dual + (audio * (1 - cvDepth) * 0.5);
    
    // Quad VCA: Full bridge for cleanest ring mod
    // Cross-coupled pairs cancel carrier more effectively
    quad = audio * cv * cvDepth;
    quad = quad + (
        (audio * SinOsc.ar(carrierFreq, pi) * cvDepth * 0.5) +  // Inverted CV
        (Saw.ar(freq * 0.999) * cv * cvDepth * 0.3)  // Slightly detuned
    );
    quad = quad + (audio * (1 - cvDepth) * 0.3);
    
    // Select topology
    vcaOut = SelectX.ar(topology, [single, dual, quad]);
    
    // OTA distortion character (exponential response)
    vcaOut = vcaOut + (vcaOut.cubed * drive * 0.2);
    
    // OTA bandwidth limiting (they roll off at high frequencies)
    sig = LPF.ar(vcaOut, drive.linexp(0, 1, 16000, 8000));
    
    // Add slight even harmonic warmth
    sig = sig + (sig.squared.sign * sig.squared * 0.05 * drive);
    
    // Stereo spread
    sig = Pan2.ar(sig, SinOsc.kr(carrierFreq * 0.01).range(-0.4, 0.4));
    
    // === FILTER ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    
    // === ENVELOPE AS FINAL VCA ===
    allTrigs = In.ar(clockTrigBus, ~clockRates.size);
    clockTrig = Select.ar(clockRate, allTrigs);
    
    env = EnvGen.ar(Env.perc(attack, decay), clockTrig);
    sig = Select.ar(envEnabled, [sig, sig * env]);
    
    sig = sig * amp;
    
    Out.ar(out, sig);
}).add;

"  ✓ vcaRing loaded".postln;
