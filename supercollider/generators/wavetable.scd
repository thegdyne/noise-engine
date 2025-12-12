/*
Wavetable Generator
Morphing waveform synthesis with unison

Signal flow: P1-P5 → Wavetable Oscillators → Unison → Filter → ENVELOPE → Output

Standard params:
  - frequency: oscillator pitch (20-8000 Hz)
  - cutoff: 1-16000 Hz
  - resonance: 0.001-1.0
  - attack/decay: final VCA envelope

Custom params:
  - custom[0] table_index: 0-1 (wavetable position, morphs through shapes)
  - custom[1] scan_rate: 0-10 Hz (automatic table scanning LFO)
  - custom[2] unison_detune: 0-1 (spread between voices)
  - custom[3] unison_voices: 1-8 discrete (number of stacked voices)
  - custom[4] interpolation: 0-2 discrete (none/linear/smooth)

ENV OFF = continuous wavetable drone
ENV ON = clock-synced envelope gates final output
*/

SynthDef(\wavetable, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                        filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                       midiTrigBus=0, slotIndex=0,
                        customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, env, freq, filterFreq, rq, filterType, attack, decay, amp;
    var envSource, clockRate, allTrigs, clockTrig, allMidiTrigs, midiTrig, trig;
    var tablePos, scanRate, detune, voices, interp;
    var tableIndex, wave1, wave2, wave3, wave4, morphedWave;
    var unisonSig, detuneAmt;
    
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
    tablePos = In.kr(customBus0);     // 0-1
    scanRate = In.kr(customBus1);     // 0-10 Hz
    detune = In.kr(customBus2);       // 0-1
    voices = In.kr(customBus3);       // 1-8
    interp = In.kr(customBus4);       // 0-2
    
    // === SOUND SOURCE (runs continuously) ===
    
    // Table index with optional scanning LFO
    tableIndex = tablePos + (SinOsc.kr(scanRate).range(0, 1) * (scanRate > 0.01));
    tableIndex = tableIndex.wrap(0, 1);
    
    // Build wavetable voices with unison
    unisonSig = Mix.fill(8, { |i|
        var voiceFreq, voicePhase, voiceWave;
        var voiceActive = (i < voices);
        
        // Detune spread (centered around base freq)
        detuneAmt = detune * 0.03;  // Max 3% detune
        voiceFreq = freq * (1 + ((i - (voices - 1) * 0.5) * detuneAmt / voices.max(1)));
        voiceFreq = voiceFreq.clip(20, 20000);
        
        // Phase offset per voice for stereo width
        voicePhase = i / 8;
        
        // === WAVETABLE MORPHING ===
        // 4 basic waveforms to morph between
        wave1 = SinOsc.ar(voiceFreq);                           // Sine
        wave2 = LFTri.ar(voiceFreq);                            // Triangle
        wave3 = LFSaw.ar(voiceFreq);                            // Saw
        wave4 = Pulse.ar(voiceFreq, 0.5);                       // Square
        
        // Morph based on table index (0-0.33: sin->tri, 0.33-0.66: tri->saw, 0.66-1: saw->square)
        voiceWave = SelectX.ar(
            tableIndex * 3,
            [wave1, wave2, wave3, wave4]
        );
        
        // Apply interpolation smoothing
        voiceWave = SelectX.ar(interp, [
            voiceWave,                                           // 0: No smoothing
            LPF.ar(voiceWave, 8000),                            // 1: Linear (mild LPF)
            LPF.ar(voiceWave, 4000)                             // 2: Smooth (stronger LPF)
        ]);
        
        voiceWave * voiceActive / voices.max(1)
    });
    
    sig = unisonSig * 0.7;
    
    // Stereo spread based on detune
    sig = Splay.ar(sig.asArray, spread: detune, center: 0);
    
    // Ensure stereo output
    sig = sig.asArray.sum;
    sig = Pan2.ar(sig, LFNoise1.kr(0.2).range(-0.3, 0.3) * detune);
    
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

"  ✓ wavetable loaded".postln;
