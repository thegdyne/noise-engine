/*
808 Clap Generator
Classic TR-808 style hand clap

Features:
  - Multiple noise bursts (simulating multiple hands)
  - Bandpass filtered noise
  - Reverb tail built-in
  - Adjustable spread between hits

Custom params:
  - P1 spread: Time spread of multiple hits
  - P2 tone: Filter center frequency
  - P3 reverb: Reverb tail amount
  - P4 attack_mod: Attack sharpness
  - P5 decay_mod: Decay/tail length
*/

SynthDef(\clap_808, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                       filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                       midiTrigBus=0, slotIndex=0,
                       customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var spread, tone, reverb, attackMod, decayMod;
    var trig, noise;
    var env1, env2, env3, env4, envTail;
    var spreadTime, claps, tail;
    
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
    spread = In.kr(customBus0);
    tone = In.kr(customBus1);
    reverb = In.kr(customBus2);
    attackMod = In.kr(customBus3);
    decayMod = In.kr(customBus4);
    
    // === TRIGGER ===
    trig = Select.ar(envSource, [
        DC.ar(0),
        Select.ar(clockRate.round, In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex, In.ar(midiTrigBus, 8))
    ]);
    
    // === MULTIPLE CLAP ENVELOPES ===
    // 808 clap has 4 quick bursts then a tail
    spreadTime = spread * 0.03;  // Max 30ms spread
    
    env1 = EnvGen.ar(Env.perc(0.001, 0.01), trig);
    env2 = EnvGen.ar(Env.perc(0.001, 0.01), DelayN.ar(trig, 0.05, spreadTime * 0.3));
    env3 = EnvGen.ar(Env.perc(0.001, 0.01), DelayN.ar(trig, 0.05, spreadTime * 0.6));
    env4 = EnvGen.ar(Env.perc(0.001, 0.015), DelayN.ar(trig, 0.05, spreadTime));
    
    // Reverb tail envelope
    envTail = EnvGen.ar(
        Env.perc(0.01, 0.15 + (decayMod * 0.3), 0.5, -4),
        DelayN.ar(trig, 0.05, spreadTime)
    );
    
    // === NOISE SOURCE ===
    noise = WhiteNoise.ar;
    
    // Bandpass filter the noise
    noise = BPF.ar(noise, 1200 + (tone * 1500), 0.7) * 3;
    
    // === CLAP BURSTS ===
    claps = noise * (env1 + env2 + env3 + env4);
    claps = claps * (0.5 + (attackMod * 0.5));
    
    // === REVERB TAIL ===
    tail = BPF.ar(WhiteNoise.ar, 1000 + (tone * 800), 1.0);
    tail = tail * envTail * reverb;
    
    // === MIX ===
    sig = claps + tail;
    sig = HPF.ar(sig, 400);  // Remove low rumble
    sig = sig.tanh;  // Soft clip
    
    // === PROCESSING CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = sig * amp;
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  ✓ clap_808 loaded".postln;
