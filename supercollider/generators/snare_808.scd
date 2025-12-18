/*
808 Snare Generator
Classic TR-808 style snare drum

Features:
  - Two-tone sine body with pitch envelope
  - Filtered noise for snare wires
  - Separate decay controls for body and noise
  - Snap/transient control

Custom params:
  - P1 tone_level: Body/tone amount
  - P2 noise_level: Snare noise amount
  - P3 snap: Attack snap intensity
  - P4 tone_decay: Body decay time
  - P5 noise_decay: Noise decay time
*/

SynthDef(\snare_808, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                        filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                        midiTrigBus=0, slotIndex=0,
                        customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var toneLevel, noiseLevel, snap, toneDecay, noiseDecay;
    var trig, pitchEnv, toneEnv, noiseEnv;
    var tone1, tone2, body, snareNoise;
    
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
    toneLevel = In.kr(customBus0);
    noiseLevel = In.kr(customBus1);
    snap = In.kr(customBus2);
    toneDecay = In.kr(customBus3);
    noiseDecay = In.kr(customBus4);
    
    // === TRIGGER ===
    trig = Select.ar(envSource, [
        DC.ar(0),
        Select.ar(clockRate.round, In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex, In.ar(midiTrigBus, 8))
    ]);
    
    // === ENVELOPES ===
    pitchEnv = EnvGen.ar(
        Env.perc(0.001, 0.03, 1, -8),
        trig
    );
    
    toneEnv = EnvGen.ar(
        Env.perc(0.001, toneDecay, 1, -6),
        trig
    );
    
    noiseEnv = EnvGen.ar(
        Env.perc(0.001, noiseDecay, 1, -4),
        trig
    );
    
    // === TONE BODY ===
    // 808 snare has two tones around 180Hz and 330Hz
    tone1 = SinOsc.ar(freq + (pitchEnv * freq * snap * 2)) * 0.7;
    tone2 = SinOsc.ar(freq * 1.8 + (pitchEnv * freq * snap)) * 0.5;
    body = (tone1 + tone2) * toneEnv * toneLevel;
    
    // === SNARE NOISE ===
    // Bandpassed noise for snare character
    snareNoise = WhiteNoise.ar;
    snareNoise = BPF.ar(snareNoise, 3000, 0.8) * 2;  // Boost bandpass
    snareNoise = HPF.ar(snareNoise, 500);  // Remove low rumble
    snareNoise = snareNoise * noiseEnv * noiseLevel;
    
    // === MIX ===
    sig = body + snareNoise;
    sig = sig.tanh;  // Soft clip
    
    // === PROCESSING CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = sig * amp;
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  ✓ snare_808 loaded".postln;
