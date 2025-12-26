/*
808 Hi-hat Generator
Classic TR-808 style hi-hat

Features:
  - 6 square wave oscillators at metallic ratios
  - Bandpass filtering for tone shaping
  - Open/closed control (decay morphing)
  - Adjustable ring/resonance

Custom params:
  - P1 open_closed: 0=closed (short), 1=open (long)
  - P2 tone: Brightness/tone color
  - P3 ring: Metallic resonance amount
  - P4 hpf: High-pass filter amount
  - P5 decay_mod: Additional decay modifier
*/

SynthDef(\hat_808, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                      filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                      midiTrigBus=0, slotIndex=0,
                      customBus0, customBus1, customBus2, customBus3, customBus4, portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var openClosed, tone, ring, hpfAmt, decayMod;
    var trig, env, decayTime;
    var metallic, freqs, oscs;
    
    // Standard params
    freq = In.kr(freqBus);
    portamento = In.kr(portamentoBus);
    freq = Lag.kr(freq, portamento.linexp(0, 1, 0.001, 0.5));
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);
    
    // Custom params
    openClosed = In.kr(customBus0);
    tone = In.kr(customBus1);
    ring = In.kr(customBus2);
    hpfAmt = In.kr(customBus3);
    decayMod = In.kr(customBus4);
    
    // === TRIGGER ===
    trig = Select.ar(envSource, [
        DC.ar(0),
        Select.ar(clockRate.round, In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex, In.ar(midiTrigBus, 8))
    ]);
    
    // === ENVELOPE ===
    // Decay morphs from ~30ms (closed) to ~300ms (open)
    decayTime = openClosed.linexp(0, 1, 0.03, 0.3) * (0.5 + decayMod);
    env = EnvGen.ar(
        Env.perc(0.001, decayTime, 1, -6),
        trig
    );
    
    // === METALLIC OSCILLATORS ===
    // 808 uses 6 square waves at non-harmonic ratios
    freqs = [205, 304, 369, 523, 800, 1156] * (0.5 + (tone * 1.0));
    oscs = Pulse.ar(freqs, 0.5);
    metallic = Mix(oscs) / 6;
    
    // Add some noise for texture
    metallic = metallic + (WhiteNoise.ar * 0.3);
    
    // === FILTERING ===
    // Bandpass for tone color
    sig = BPF.ar(metallic, 8000 + (tone * 4000), 0.5 + (ring * 0.5));
    
    // High-pass to remove body
    sig = HPF.ar(sig, 4000 + (hpfAmt * 6000));
    
    // Resonant peak for ring
    sig = sig + (BPF.ar(metallic, 10000, 0.1) * ring * 2);
    
    // Apply envelope
    sig = sig * env;
    sig = sig.tanh;  // Soft limit
    
    // === PROCESSING CHAIN ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = sig * amp;
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  [x] hat_808 loaded".postln;
