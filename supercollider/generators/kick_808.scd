/*
808 Kick Generator
Classic TR-808 style kick drum

Features:
  - Sine oscillator with pitch envelope
  - Adjustable punch (pitch sweep depth)
  - Tone control (fundamental/harmonics balance)
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
    var trig, pitchEnv, ampEnv, body, bodyWithHarmonics, clickSig, harmonics;
    
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
    drive = Lag.kr(drive, 0.02);  // Smooth to prevent zipper noise
    click = In.kr(customBus4);
    
    // === TRIGGER ===
    // Clamp indices for safety
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);
    
    // === ENVELOPES ===
    // Pitch envelope - fixed fast time, punch controls depth only
    pitchEnv = EnvGen.ar(
        Env.perc(0.001, 0.06, 1, -8),  // Fixed 60ms decay for consistent 808 thump
        trig
    );
    
    // Amplitude envelope
    ampEnv = EnvGen.ar(
        Env.perc(0.001, decayTime, 1, -4),
        trig
    );
    
    // === SOUND SOURCE ===
    // Main body - sine with pitch sweep (punch = depth only)
    body = SinOsc.ar(freq + (pitchEnv * freq * punch * 4));
    
    // Harmonics for tone - slightly detuned 3rd partial for analog character
    harmonics = SinOsc.ar(freq * 2) * 0.3;
    harmonics = harmonics + (SinOsc.ar(freq * 2.98) * 0.1);  // Subtle inharmonicity
    
    // Body with harmonics mixed
    bodyWithHarmonics = body + harmonics;
    
    // Tone as true balance: crossfade from pure body to body+harmonics
    sig = XFade2.ar(body, bodyWithHarmonics, (tone * 2) - 1);
    
    // Apply amp envelope to body
    sig = sig * ampEnv;
    
    // Click transient - mixed post-ampEnv so it stays punchy
    clickSig = HPF.ar(WhiteNoise.ar, 1000) * EnvGen.ar(Env.perc(0.001, 0.015), trig);
    sig = sig + (clickSig * click);
    
    // === SATURATION ===
    sig = (sig * (1 + (drive * 3))).tanh;
    
    // === PROCESSING CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = sig * amp;
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  ✓ kick_808 loaded".postln;
