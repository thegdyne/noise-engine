/*
Subtractive Generator
Classic oscillator + filter synthesis

Signal flow: P1-P5 → Oscillators → Mix → Filter → ENVELOPE → Output

Standard params:
  - frequency: base oscillator pitch (20-8000 Hz)
  - cutoff: 1-16000 Hz
  - resonance: 0.001-1.0
  - attack/decay: final VCA envelope

Custom params:
  - custom[0] osc_waveform: 0-3 (saw/square/tri/noise)
  - custom[1] sub_osc_level: 0-1 (sub oscillator amount)
  - custom[2] osc_mix: 0-1 (OSC1 <-> OSC2 crossfade)
  - custom[3] noise_amount: 0-1 (noise layer)
  - custom[4] filter_drive: 0-1 (pre-filter saturation)

ENV OFF = drone (continuous output)
ENV ON = clock-synced envelope gates final output
*/

SynthDef(\subtractive, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                          filterTypeBus, envEnabledBus, clockRateBus, clockTrigBus,
                          midiTrigBus=0, slotIndex=0,
                          customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, env, freq, filterFreq, rq, filterType, attack, decay, amp;
    var envEnabled, clockRate, allTrigs, clockTrig, midiTrig, combinedTrig;
    var waveform, subLevel, oscMix, noiseAmt, drive;
    var osc1, osc2, sub, noise, saw, square, tri, noiseOsc;
    
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
    
    // Read custom params (values come pre-mapped from GUI)
    waveform = In.kr(customBus0);    // 0-3 discrete
    subLevel = In.kr(customBus1);    // 0-1
    oscMix = In.kr(customBus2);      // 0-1
    noiseAmt = In.kr(customBus3);    // 0-1
    drive = In.kr(customBus4);       // 0-1
    
    // === SOUND SOURCE (runs continuously) ===
    
    // Core waveforms
    saw = Saw.ar(freq);
    square = Pulse.ar(freq, 0.5);
    tri = LFTri.ar(freq);
    noiseOsc = WhiteNoise.ar;
    
    // Waveform select (0=saw, 1=square, 2=tri, 3=noise)
    osc1 = SelectX.ar(waveform, [saw, square, tri, noiseOsc]);
    
    // Second oscillator slightly detuned for thickness
    osc2 = SelectX.ar(waveform, [
        Saw.ar(freq * 1.005),
        Pulse.ar(freq * 0.995, 0.45),
        LFTri.ar(freq * 1.003),
        PinkNoise.ar
    ]);
    
    // Sub oscillator (one octave down, square wave for punch)
    sub = Pulse.ar(freq * 0.5, 0.5) * subLevel;
    
    // Noise layer
    noise = WhiteNoise.ar * noiseAmt * 0.5;
    
    // Mix oscillators
    sig = ((osc1 * (1 - oscMix)) + (osc2 * oscMix)) * 0.5;
    sig = sig + sub + noise;
    
    // Pre-filter drive/saturation
    sig = (sig * (1 + (drive * 4))).tanh;
    
    // Stereo spread from slight pitch wobble
    sig = Pan2.ar(sig, LFNoise1.kr(0.3).range(-0.3, 0.3));
    
    // === FILTER ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    
    // === ENVELOPE AS FINAL VCA ===
    // Clock triggers
    allTrigs = In.ar(clockTrigBus, ~clockRates.size);
    clockTrig = Select.ar(clockRate, allTrigs);
    
    // MIDI trigger for this slot
    midiTrig = In.ar(midiTrigBus, 8)[slotIndex];
    
    // Combine clock and MIDI triggers
    combinedTrig = clockTrig + midiTrig;
    
    env = EnvGen.ar(Env.perc(attack, decay), combinedTrig);
    sig = Select.ar(envEnabled, [sig, sig * env]);
    
    sig = sig * amp;
    
    Out.ar(out, sig);
}).add;

"  ✓ subtractive loaded".postln;
