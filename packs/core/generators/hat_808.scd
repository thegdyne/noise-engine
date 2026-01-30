// core/hat_808 — Lightweight end-stage generator
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

SynthDef(\hat_808, { |out, freqBus, customBus0|
    var sig, freq;
    var p = In.kr(customBus0, 5);
    var openClosed, tone, ring, hpfAmt, decayMod;
    var trig, env, decayTime;
    var metallic, freqs, oscs;

    freq = In.kr(freqBus);

    openClosed = p[0];
    tone = p[1];
    ring = p[2];
    hpfAmt = p[3];
    decayMod = p[4];

    // One-shot trigger (end-stage handles retriggering)
    trig = Impulse.ar(0);

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

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] hat_808 loaded".postln;
