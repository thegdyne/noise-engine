/*
Diode Ring Generator
Passive diode ring balanced modulator
Based on Elektor Formant synthesiser (May 1977 - April 1978) - C. Chapman

Signal flow: P1-P5 → Carrier + Modulator → Ring Mod → Filter → ENVELOPE → Output

Models classic passive diode ring:
- Four diodes in bridge configuration
- Transformer-coupled carrier and modulator inputs
- Produces sum and difference frequencies (sidebands)
- Carrier suppression depends on balance trim
- Natural compression and soft clipping

Standard params:
  - frequency: carrier pitch (20-8000 Hz)
  - cutoff: 1-16000 Hz
  - resonance: 0.001-1.0
  - attack/decay: final VCA envelope

Custom params:
  - custom[0] carrier_freq: 20-2000 Hz (internal carrier)
  - custom[1] modulator_freq: 0.1-1000 Hz (modulator for sidebands)
  - custom[2] input_level: 0-1 (sideband strength)
  - custom[3] balance: 0-1 (bridge symmetry, carrier suppression)
  - custom[4] carrier_leak: 0-1 (carrier bleed-through)

ENV OFF = continuous ring modulation
ENV ON = clock-synced envelope gates final output
*/

SynthDef(\diodeRing, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                        filterTypeBus, envEnabledBus, clockRateBus, clockTrigBus,
                        customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, env, freq, filterFreq, rq, filterType, attack, decay, amp;
    var envEnabled, clockRate, allTrigs, clockTrig;
    var carrierFreq, modFreq, level, balance, leak;
    var carrier, modulator, ringOut, diodeChar;
    
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
    level = In.kr(customBus2);         // 0-1
    balance = In.kr(customBus3);       // 0-1
    leak = In.kr(customBus4);          // 0-1
    
    // === SOUND SOURCE (runs continuously) ===
    
    // Use frequency param to offset carrier
    carrierFreq = carrierFreq * freq.linlin(20, 8000, 0.5, 2);
    carrierFreq = carrierFreq.clip(20, 20000);
    
    // Carrier oscillator (transformer-coupled, slight saturation)
    carrier = SinOsc.ar(carrierFreq);
    carrier = (carrier * 1.2).tanh;  // Soft transformer saturation
    
    // Modulator oscillator
    modulator = SinOsc.ar(modFreq);
    modulator = (modulator * 1.1).tanh;
    
    // === DIODE RING MULTIPLICATION ===
    
    // Ideal ring mod is simple multiplication
    ringOut = carrier * modulator;
    
    // Diode nonlinearity adds harmonics and asymmetry
    // Balance affects how symmetric the diode pairs are
    diodeChar = balance.linlin(0, 1, 0.9, 1.0);  // Perfect = 1.0
    ringOut = ringOut * diodeChar;
    
    // Unbalanced diodes add even harmonics and carrier leak
    ringOut = ringOut + (carrier * (1 - diodeChar) * 0.2);
    
    // Diode forward voltage creates soft clipping
    ringOut = (ringOut * (1 + (level * 2))).fold(-1, 1);
    
    // Add slight odd harmonic distortion (diode knee)
    ringOut = ringOut + (ringOut.cubed * 0.1 * level);
    
    // Carrier leak (deliberate bleed-through)
    sig = ringOut + (carrier * leak * 0.5);
    
    // Apply input level (affects sideband strength)
    sig = sig * level.linlin(0, 1, 0.3, 1);
    
    // Transformer coloration (slight bandwidth limiting)
    sig = LPF.ar(HPF.ar(sig, 40), 12000);
    
    // Stereo spread
    sig = Pan2.ar(sig, SinOsc.kr(modFreq * 0.01).range(-0.3, 0.3));
    
    // === FILTER ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    
    // === ENVELOPE AS FINAL VCA ===
    allTrigs = In.ar(clockTrigBus, 12);
    clockTrig = Select.ar(clockRate, allTrigs);
    
    env = EnvGen.ar(Env.perc(attack, decay), clockTrig);
    sig = Select.ar(envEnabled, [sig, sig * env]);
    
    sig = sig * amp;
    
    Out.ar(out, sig);
}).add;

"  ✓ diodeRing loaded".postln;
