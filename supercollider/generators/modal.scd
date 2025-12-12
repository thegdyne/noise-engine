/*
Modal Generator
Resonant body physical modeling

Signal flow: Exciter → Modal Resonators → Filter → ENV VCA → Output

Custom params:
  - P1 material: 0-1 (wood <-> metal <-> glass)
  - P2 brightness: 0-1 (muted <-> bright)
  - P3 decay_shape: 0-1 (quick <-> ringing)
  - P4 density: 1-20 (number of modes)
  - P5 retrig_rate: 0.1-50 Hz (internal strike rate)

MIDI retrig mode: When envSource=MIDI, external triggers drive the exciter
at ~30Hz while key is held. The retrig_rate param is ignored in this mode.
*/

SynthDef(\modal, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                    filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                    midiTrigBus=0, slotIndex=0,
                    customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var material, brightness, decayShape, density, retrigRate;
    var exciter, modes, exciterTrig;
    var allMidiTrigs, midiTrig;
    
    // Standard params
    freq = In.kr(freqBus);
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);
    
    // Custom params
    material = In.kr(customBus0);
    brightness = In.kr(customBus1);
    decayShape = In.kr(customBus2);
    density = In.kr(customBus3);
    retrigRate = In.kr(customBus4);
    
    // === EXCITER TRIGGER ===
    // In MIDI mode (envSource=2), use MIDI trigger bus (continuous 30Hz from held key)
    // Otherwise use internal retrig rate
    allMidiTrigs = In.ar(midiTrigBus, 8);
    midiTrig = Select.ar(slotIndex, allMidiTrigs);
    
    exciterTrig = Select.ar(envSource > 1, [
        Impulse.ar(retrigRate),  // Internal retrig (envSource 0 or 1)
        midiTrig                  // MIDI retrig (envSource 2)
    ]);
    
    // === SOUND SOURCE ===
    exciter = WhiteNoise.ar * EnvGen.ar(Env.perc(0.0001, 0.005), exciterTrig);
    
    modes = Mix.fill(12, { |i|
        var modeFreq, modeAmp, modeDecay, ratio;
        ratio = [1, 2.0, 3.0, 4.2, 5.4, 6.8, 8.2, 9.8, 11.5, 13.3, 15.2, 17.3][i];
        ratio = ratio * material.linlin(0, 1, 0.95, 1.05);
        modeFreq = (freq * ratio).clip(20, 18000);
        modeAmp = (1 / (i + 1)) * (1 - (material * 0.3 * i / 12));
        modeDecay = decayShape.linexp(0, 1, 0.05, 2) / (i + 1);
        
        Ringz.ar(exciter, modeFreq, modeDecay) * modeAmp * (i < density)
    }) * brightness.linlin(0, 1, 0.3, 1);
    
    sig = modes * 0.2;
    
    // === PROCESSING CHAIN ===
    sig = ~stereoSpread.(sig, 0.15, 0.4);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    
    Out.ar(out, sig);
}).add;

"  ✓ modal loaded".postln;
