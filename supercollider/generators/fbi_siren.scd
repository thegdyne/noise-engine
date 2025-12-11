/*
FBI Siren Generator
NE556 dual-timer wailing siren with lamp flash
Based on Elektor Magazine March 2006 "FBI siren with flashing light" - Arthur Schilp

Signal flow: P1-P5 → LFO Timer → Audio VCO → Filter → ENVELOPE → Output

Models the dual 555 (NE556) circuit:
- Timer 1: Slow astable (~2Hz) for sweep LFO and lamp flash
- Timer 2: Audio VCO controlled by Timer 1's capacitor voltage
- Smooth wailing sweep as cap charges/discharges
- Classic American police/FBI siren sound

Standard params:
  - frequency: audio VCO base pitch (20-8000 Hz)
  - cutoff: 1-16000 Hz
  - resonance: 0.001-1.0
  - attack/decay: final VCA envelope

Custom params:
  - custom[0] audio_rc: 0-1 (audio timer RC, nominal pitch)
  - custom[1] lfo_rate: 0.1-10 Hz (sweep/wail speed)
  - custom[2] mod_depth: 0-1 (pitch sweep range)
  - custom[3] mod_curve: 0-1 (sweep shape, exponential vs linear)
  - custom[4] drive_level: 0-1 (speaker overdrive)

ENV OFF = continuous wailing siren
ENV ON = clock-synced envelope gates final output
*/

SynthDef(\fbiSiren, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                       filterTypeBus, envEnabledBus, clockRateBus, clockTrigBus,
                       customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, env, freq, filterFreq, rq, filterType, attack, decay, amp;
    var envEnabled, clockRate, allTrigs, clockTrig;
    var audioRC, lfoRate, modDepth, modCurve, drive;
    var lfo, sweepVoltage, audioFreq, triangle;
    
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
    audioRC = In.kr(customBus0);       // 0-1
    lfoRate = In.kr(customBus1);       // 0.1-10 Hz
    modDepth = In.kr(customBus2);      // 0-1
    modCurve = In.kr(customBus3);      // 0-1
    drive = In.kr(customBus4);         // 0-1
    
    // === SOUND SOURCE (runs continuously) ===
    
    // Timer 1: Slow sweep LFO (capacitor charge/discharge simulation)
    // Triangle wave represents cap voltage rising and falling
    triangle = LFTri.kr(lfoRate, 0, 0.5, 0.5);  // 0 to 1
    
    // Apply curve shaping (555 RC curve is not perfectly linear)
    // modCurve: 0 = linear, 1 = exponential
    sweepVoltage = triangle.pow(modCurve.linlin(0, 1, 1, 2));
    
    // Timer 2: Audio VCO frequency controlled by sweep voltage
    // Higher CV = higher frequency (555 VCO characteristic)
    audioFreq = freq * audioRC.linexp(0, 1, 0.5, 2);
    audioFreq = audioFreq * (1 + (sweepVoltage * modDepth * 2));  // Sweep range
    audioFreq = audioFreq.clip(20, 20000);
    
    // 555 audio output is square wave
    sig = Pulse.ar(audioFreq, 0.5);
    
    // Add slight duty cycle variation for more analog character
    sig = sig + (Pulse.ar(audioFreq, sweepVoltage.linlin(0, 1, 0.45, 0.55)) * 0.2);
    
    // Speaker/driver overdrive character
    sig = (sig * (1 + (drive * 6))).tanh;
    
    // Add some speaker resonance at high drive
    sig = sig + (BPF.ar(sig, 800, 0.5) * drive * 0.3);
    
    // Slight instability/jitter (component tolerances)
    sig = sig * (1 + (LFNoise1.kr(10) * 0.005));
    
    // Stereo: slight pan following sweep
    sig = Pan2.ar(sig, sweepVoltage.linlin(0, 1, -0.3, 0.3));
    
    // === FILTER ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    
    // === ENVELOPE AS FINAL VCA ===
    allTrigs = In.ar(clockTrigBus, 13);
    clockTrig = Select.ar(clockRate, allTrigs);
    
    env = EnvGen.ar(Env.perc(attack, decay), clockTrig);
    sig = Select.ar(envEnabled, [sig, sig * env]);
    
    sig = sig * amp;
    
    Out.ar(out, sig);
}).add;

"  ✓ fbiSiren loaded".postln;
