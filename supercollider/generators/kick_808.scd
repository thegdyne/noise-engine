/*
808 Kick Generator
Classic TR-808 style kick drum

Features:
  - Sine oscillator with pitch envelope
  - Adjustable punch (pitch sweep)
  - Tone control (harmonic content)
  - Soft saturation for warmth
  - Click transient layer

Custom params:
  - P1 punch: Pitch envelope depth
  - P2 tone: Tone/body balance
  - P3 decay_time: Overall decay length
  - P4 drive: Saturation amount
  - P5 click: Click transient level
*/

SynthDef(\kick_808, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                       filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                       midiTrigBus=0, slotIndex=0,
                       customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var punch, tone, decayTime, drive, click;
    var trig, pitchEnv, ampEnv, body, clickSig, harmonics;
    
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
    punch = In.kr(customBus0);
    tone = In.kr(customBus1);
    decayTime = In.kr(customBus2);
    drive = In.kr(customBus3);
    click = In.kr(customBus4);
    
    // === TRIGGER ===
    trig = Select.ar(envSource, [
        DC.ar(0),
        Select.ar(clockRate.round, In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex, In.ar(midiTrigBus, 8))
    ]);
    
    // === ENVELOPES ===
    // Pitch envelope - fast exponential drop
    pitchEnv = EnvGen.ar(
        Env.perc(0.001, 0.08 * (1 + punch), 1, -8),
        trig
    );
    
    // Amplitude envelope
    ampEnv = EnvGen.ar(
        Env.perc(0.001, decayTime, 1, -4),
        trig
    );
    
    // === SOUND SOURCE ===
    // Main body - sine with pitch sweep
    body = SinOsc.ar(freq + (pitchEnv * freq * punch * 4));
    
    // Add some harmonics for tone
    harmonics = SinOsc.ar(freq * 2) * 0.3 * tone;
    harmonics = harmonics + (SinOsc.ar(freq * 3) * 0.1 * tone);
    
    // Click transient
    clickSig = HPF.ar(WhiteNoise.ar, 1000) * EnvGen.ar(Env.perc(0.001, 0.01), trig);
    
    // Mix
    sig = body + harmonics + (clickSig * click);
    sig = sig * ampEnv;
    
    // === SATURATION ===
    sig = (sig * (1 + (drive * 3))).tanh;
    
    // === PROCESSING CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = sig * amp;
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  ✓ kick_808 loaded".postln;
