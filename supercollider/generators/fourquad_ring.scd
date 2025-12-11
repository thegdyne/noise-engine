/*
4-Quad Ring Generator
Four-quadrant multiplier ring modulator (MC1496/AD633 style)
Based on Elektor Formant mk II add-on modules (1977-1978) - C. Chapman

Signal flow: P1-P5 → Carrier × Modulator → Filter → ENVELOPE → Output

Models active 4-quadrant analog multiplier:
- True mathematical multiplication (X × Y)
- Works in all four quadrants (both polarities)
- Better carrier suppression than diode ring
- Offset null allows fine-tuning
- More linear than passive designs

Standard params:
  - frequency: carrier pitch (20-8000 Hz)
  - cutoff: 1-16000 Hz
  - resonance: 0.001-1.0
  - attack/decay: final VCA envelope

Custom params:
  - custom[0] carrier_freq: 20-2000 Hz (X input frequency)
  - custom[1] modulator_freq: 0.1-1000 Hz (Y input frequency)
  - custom[2] gain: 0-1 (multiplication gain factor)
  - custom[3] linearity: 0-1 (bias/linearity trim, affects distortion)
  - custom[4] offset_null: 0-1 (carrier null adjustment, purity)

ENV OFF = continuous ring modulation
ENV ON = clock-synced envelope gates final output
*/

SynthDef(\fourQuadRing, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                           filterTypeBus, envEnabledBus, clockRateBus, clockTrigBus,
                           customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, env, freq, filterFreq, rq, filterType, attack, decay, amp;
    var envEnabled, clockRate, allTrigs, clockTrig;
    var carrierFreq, modFreq, gain, linearity, offsetNull;
    var carrier, modulator, product, dcOffset;
    
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
    carrierFreq = In.kr(customBus0);   // 20-2000 Hz
    modFreq = In.kr(customBus1);       // 0.1-1000 Hz
    gain = In.kr(customBus2);          // 0-1
    linearity = In.kr(customBus3);     // 0-1
    offsetNull = In.kr(customBus4);    // 0-1
    
    // === SOUND SOURCE (runs continuously) ===
    
    // Use frequency param to offset carrier
    carrierFreq = carrierFreq * freq.linlin(20, 8000, 0.5, 2);
    carrierFreq = carrierFreq.clip(20, 20000);
    
    // X input: Carrier (can be various waveforms for different timbres)
    carrier = SinOsc.ar(carrierFreq);
    
    // Y input: Modulator
    modulator = SinOsc.ar(modFreq);
    
    // === 4-QUADRANT MULTIPLICATION ===
    
    // True multiplication (the ideal behavior)
    product = carrier * modulator;
    
    // Apply gain (K factor in multiplier)
    product = product * gain.linlin(0, 1, 0.3, 1.5);
    
    // Linearity affects how clean the multiplication is
    // Low linearity = more harmonic distortion (bias errors)
    product = product + (product.cubed * (1 - linearity) * 0.2);
    product = product + (product.squared.sign * product.squared * (1 - linearity) * 0.1);
    
    // DC offset from imperfect null adjustment
    // Creates carrier feedthrough
    dcOffset = (1 - offsetNull) * 0.1;
    product = product + (carrier * dcOffset * 0.3);
    product = product + (modulator * dcOffset * 0.15);
    
    // Op-amp bandwidth limiting (slight HF rolloff)
    sig = LPF.ar(product, linearity.linexp(0, 1, 8000, 16000));
    
    // Add second harmonic interaction for richness
    sig = sig + (SinOsc.ar(carrierFreq + modFreq) * SinOsc.ar(carrierFreq - modFreq) * 0.1 * (1 - linearity));
    
    // Stereo spread based on modulation
    sig = Pan2.ar(sig, SinOsc.kr(modFreq * 0.02).range(-0.4, 0.4));
    
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

"  ✓ fourQuadRing loaded".postln;
