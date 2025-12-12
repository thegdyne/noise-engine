/*
FBI Siren Doppler Generator
NE556 dual-timer wailing siren with Doppler passing effect

Based on FBI Siren but adds realistic Doppler shift as if 
emergency vehicle is approaching then passing by.

Doppler effect includes:
- Pitch shift (higher approaching, lower receding)
- Volume swell (louder as it passes)
- Stereo pan (left to right or right to left)
- High frequency rolloff when receding (air absorption)

Standard params:
  - frequency: audio VCO base pitch (20-8000 Hz)
  - cutoff: 1-16000 Hz
  - resonance: 0.001-1.0
  - attack/decay: final VCA envelope

Custom params:
  - custom[0] audio_rc: 0-1 (audio timer RC, nominal pitch)
  - custom[1] lfo_rate: 0.1-10 Hz (sweep/wail speed)
  - custom[2] mod_depth: 0-1 (pitch sweep range)
  - custom[3] pass_rate: 0.02-2 Hz (how fast vehicle passes)
  - custom[4] doppler_amt: 0-1 (intensity of doppler effect)

ENV OFF = continuous passing sirens
ENV ON = clock-synced envelope gates final output
*/

SynthDef(\fbiDoppler, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                       filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                       midiTrigBus=0, slotIndex=0,
                       customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, env, freq, filterFreq, rq, filterType, attack, decay, amp;
    var envSource, clockRate, allTrigs, clockTrig, allMidiTrigs, midiTrig, trig;
    var audioRC, lfoRate, modDepth, passRate, dopplerAmt;
    var lfo, sweepVoltage, audioFreq, triangle;
    var passPhase, distance, dopplerShift, dopplerPan, dopplerVol, dopplerFilter;
    
    // Read standard params
    freq = In.kr(freqBus);
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);  // 0=OFF, 1=CLK, 2=MIDI
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);
    
    // Read custom params
    audioRC = In.kr(customBus0);       // 0-1
    lfoRate = In.kr(customBus1);       // 0.1-10 Hz
    modDepth = In.kr(customBus2);      // 0-1
    passRate = In.kr(customBus3);      // 0.02-2 Hz
    dopplerAmt = In.kr(customBus4);    // 0-1
    
    // === DOPPLER PASS TRAJECTORY ===
    // Sine wave represents position: -1 = far left approaching, 0 = passing, 1 = far right receding
    passPhase = SinOsc.kr(passRate, -0.5pi);  // Start at -1 (approaching)
    
    // Distance from listener (closest at 0, furthest at -1 or 1)
    distance = passPhase.abs;
    
    // Doppler pitch shift: approaching = higher, receding = lower
    // Real doppler is about ±6% at 60mph passing, we'll exaggerate for effect
    dopplerShift = passPhase.neg.linlin(-1, 1, 0.88, 1.12);  // ±12% shift
    dopplerShift = dopplerShift.blend(1, 1 - dopplerAmt);    // Blend with no shift
    
    // === SIREN OSCILLATOR ===
    
    // Timer 1: Slow sweep LFO (capacitor charge/discharge)
    triangle = LFTri.kr(lfoRate, 0, 0.5, 0.5);  // 0 to 1
    
    // Slight RC curve shaping
    sweepVoltage = triangle.pow(1.3);
    
    // Timer 2: Audio VCO frequency with doppler applied
    audioFreq = freq * audioRC.linexp(0, 1, 0.5, 2);
    audioFreq = audioFreq * (1 + (sweepVoltage * modDepth * 2));
    audioFreq = audioFreq * dopplerShift;  // Apply doppler
    audioFreq = audioFreq.clip(20, 20000);
    
    // 555 square wave output
    sig = Pulse.ar(audioFreq, 0.5);
    
    // Slight duty cycle wobble
    sig = sig + (Pulse.ar(audioFreq * 1.001, sweepVoltage.linlin(0, 1, 0.47, 0.53)) * 0.15);
    
    // Some speaker character
    sig = (sig * 1.5).tanh;
    sig = sig + (BPF.ar(sig, 900, 0.4) * 0.2);
    
    // === DOPPLER DISTANCE EFFECTS ===
    
    // Volume: louder when close (at passPhase = 0)
    dopplerVol = distance.linlin(0, 1, 1, 0.3);
    dopplerVol = dopplerVol.blend(1, 1 - dopplerAmt);
    sig = sig * dopplerVol;
    
    // High frequency rolloff when distant (air absorption)
    dopplerFilter = distance.linexp(0, 1, 12000, 2000);
    dopplerFilter = dopplerFilter.blend(12000, 1 - dopplerAmt);
    sig = LPF.ar(sig, dopplerFilter);
    
    // Stereo pan following position
    dopplerPan = passPhase * dopplerAmt;
    sig = Pan2.ar(sig, dopplerPan);
    
    // Add slight reverb tail for distance (simple comb)
    sig = sig + (CombL.ar(sig, 0.1, distance.linlin(0, 1, 0.02, 0.08), distance * 0.5 * dopplerAmt) * 0.15);
    
    // === FILTER ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    
    // === ENVELOPE AS FINAL VCA ===
    // Clock trigger
    allTrigs = In.ar(clockTrigBus, ~clockRates.size);
    clockTrig = Select.ar(clockRate, allTrigs);
    
    // MIDI trigger - read all 8 channels and select by slotIndex
    allMidiTrigs = In.ar(midiTrigBus, 8);
    midiTrig = Select.ar(slotIndex, allMidiTrigs);
    
    // Select trigger based on envSource: 0=none, 1=clock, 2=midi
    trig = Select.ar(envSource, [
        DC.ar(0),      // 0: OFF - no triggers
        clockTrig,     // 1: CLK - clock triggers only  
        midiTrig       // 2: MIDI - midi triggers only
    ]);
    
    // Envelope
    env = EnvGen.ar(Env.perc(attack, decay), trig);
    
    // Apply envelope only when envSource > 0, otherwise drone
    sig = sig * Select.kr(envSource > 0, [1.0, env]) * amp;
    
    Out.ar(out, sig);
}).add;

"  ✓ fbiDoppler loaded".postln;
