/*
Karplus-Strong Generator
Physical modeling string/pluck synthesis

Signal flow: Exciter → Delay Loop → Filter → ENV VCA → Output

Custom params:
  - P1 exciter_color: 0-1 (dark thump <-> bright click)
  - P2 damping: 0-1 (string brightness/decay)
  - P3 feedback: 0.9-0.999 (sustain length)
  - P4 stretch: 0-1 (inharmonicity)
  - P5 retrig_rate: 0.1-50 Hz (internal pluck rate)

MIDI retrig mode: When envSource=MIDI, external triggers drive the exciter
at ~30Hz while key is held. The retrig_rate param is ignored in this mode.
*/

SynthDef(\karplusStrong, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                            filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                            midiTrigBus=0, slotIndex=0,
                            customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var excColor, lpfCoeff, fbGain, stretch, retrigRate;
    var exciter, delayTime, delayed, loopSig, loopFilter, exciterTrig;
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
    excColor = In.kr(customBus0);
    lpfCoeff = In.kr(customBus1);
    fbGain = In.kr(customBus2);
    stretch = In.kr(customBus3);
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
    delayTime = (1 / freq.clip(20, 8000)) * stretch.linlin(0, 1, 1, 1.02);
    delayTime = delayTime.clip(0.00005, 0.05);
    
    exciter = SelectX.ar(excColor, [
        PinkNoise.ar * EnvGen.ar(Env.perc(0.001, 0.02), exciterTrig),
        (Impulse.ar(0) + (WhiteNoise.ar * 0.7)) * EnvGen.ar(Env.perc(0.0001, 0.01), exciterTrig)
    ]);
    
    loopSig = LocalIn.ar(1);
    delayed = DelayC.ar(exciter + loopSig, 0.05, delayTime);
    loopFilter = LPF.ar(delayed, lpfCoeff.linexp(0, 1, 500, 12000));
    loopFilter = loopFilter * fbGain;
    LocalOut.ar(loopFilter);
    
    sig = delayed;
    
    // === PROCESSING CHAIN ===
    sig = ~stereoSpread.(sig, 0.3, 0.2);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp * 2, clockTrigBus, midiTrigBus, slotIndex);
    
    Out.ar(out, sig);
}).add;

"  ✓ karplusStrong loaded".postln;
