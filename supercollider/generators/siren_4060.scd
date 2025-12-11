/*
4060 Siren Generator
CD4060 counter/oscillator with analog mux siren
Based on Elektor Magazine December 2006 i-TRIXX "When the siren sounds..."

Signal flow: P1-P5 → Counter → Mux → Tone Oscillator → Filter → ENVELOPE → Output

Models the CD4060 siren circuit:
- Internal RC oscillator sets base rate
- 14-stage binary counter divides clock
- Counter outputs select resistors via analog mux
- Selected resistance sets tone oscillator pitch
- Result: stepped pitch patterns for siren effect

Standard params:
  - frequency: base tone pitch (20-8000 Hz)
  - cutoff: 1-16000 Hz
  - resonance: 0.001-1.0
  - attack/decay: final VCA envelope

Custom params:
  - custom[0] osc_resistance: 0-1 (tone VCO base frequency)
  - custom[1] resistor_pattern: 0-7 discrete (pitch step sequence)
  - custom[2] tone_cap: 0-1 (sweep speed/rate)
  - custom[3] counter_bits: 2-8 discrete (pattern complexity)
  - custom[4] drive_level: 0-1 (output saturation)

ENV OFF = continuous siren wail
ENV ON = clock-synced envelope gates final output
*/

SynthDef(\siren4060, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                        filterTypeBus, envEnabledBus, clockRateBus, clockTrigBus,
                        customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, env, freq, filterFreq, rq, filterType, attack, decay, amp;
    var envEnabled, clockRate, allTrigs, clockTrig;
    var oscRes, pattern, toneCap, counterBits, drive;
    var counterRate, counter, muxOut, toneFreq;
    var patternRatios, selectedRatio;
    
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
    oscRes = In.kr(customBus0);        // 0-1
    pattern = In.kr(customBus1);       // 0-7 discrete
    toneCap = In.kr(customBus2);       // 0-1
    counterBits = In.kr(customBus3);   // 2-8
    drive = In.kr(customBus4);         // 0-1
    
    // === SOUND SOURCE (runs continuously) ===
    
    // Counter clock rate (internal RC oscillator)
    counterRate = toneCap.linexp(0, 1, 0.5, 20);  // Steps per second
    
    // Counter (0 to 2^bits - 1, cycling)
    counter = LFSaw.kr(counterRate / counterBits.max(2), 0, 0.5, 0.5);
    counter = (counter * 16).floor / 16;  // Quantize to 16 steps
    
    // Pattern-dependent frequency ratios (resistor ladder values)
    // Different patterns give different siren characters
    patternRatios = Select.kr(pattern.round, [
        // 0: Rising siren (police style)
        counter.linlin(0, 1, 0.5, 2),
        // 1: Falling siren
        counter.linlin(0, 1, 2, 0.5),
        // 2: Two-tone (European style)
        (LFPulse.kr(counterRate * 2) * 0.5) + 0.75,
        // 3: Wail (up-down-up-down)
        (LFTri.kr(counterRate) * 0.4) + 1.0,
        // 4: Yelp (rapid alternating)
        (LFPulse.kr(counterRate * 4) * 0.3) + 0.85,
        // 5: Stepped scale
        (counter.pow(0.5) * 1.5) + 0.5,
        // 6: Random-ish
        (LFNoise0.kr(counterRate * 2) * 0.3) + 1.0,
        // 7: Phaser (slow sweep with steps)
        (counter * SinOsc.kr(0.3).range(0.8, 1.2))
    ]);
    
    // Tone oscillator frequency
    toneFreq = freq * oscRes.linexp(0, 1, 0.5, 2) * patternRatios;
    toneFreq = toneFreq.clip(20, 20000);
    
    // Square wave tone (like 555/4060 output)
    sig = Pulse.ar(toneFreq, 0.5);
    
    // Add some harmonic richness
    sig = sig + (Pulse.ar(toneFreq * 2.01, 0.5) * 0.3);
    sig = sig + (Pulse.ar(toneFreq * 0.5, 0.5) * 0.2);
    
    // Drive/saturation (loudspeaker overdrive character)
    sig = (sig * (1 + (drive * 4))).tanh;
    
    // Slight detuning wobble (component tolerances)
    sig = sig * (1 + (LFNoise1.kr(5) * 0.01));
    
    // Stereo spread
    sig = Pan2.ar(sig, SinOsc.kr(counterRate * 0.1).range(-0.4, 0.4));
    
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

"  ✓ siren4060 loaded".postln;
