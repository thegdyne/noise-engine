// electric-shepherd/static — Lightweight end-stage generator
/*
STATIC Generator
Electromagnetic field - radio ghosts and interference

Features:
  - Radio interference noise
  - Ghost signal fragments
  - Signal degradation
  - Carrier wave tone
  - EMF burst events

Custom params:
  - P1 interference: Background static
  - P2 ghost: Fragmentary signals
  - P3 degrade: Bitcrushed decay
  - P4 carrier: Underlying tone
  - P5 burst: Sudden EMF events

The electromagnetic whispers of dying technology.
*/

SynthDef(\static, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var interference, ghost, degrade, carrier, burst;
    var interferenceSig, ghostSig, degradeSig, carrierSig, burstSig;
    var intNoise, intMod;
    var ghostOsc, ghostMod, ghostGate;
    var degradeOsc, degradeBits;
    var carrierOsc, carrierMod;
    var burstTrig, burstOsc;

    freq = In.kr(freqBus);

    // Custom params with smoothing
    interference = p[0];
    interference = Lag.kr(interference, 0.05);
    ghost = p[1];
    degrade = p[2];
    degrade = Lag.kr(degrade, 0.05);
    carrier = p[3];
    carrier = Lag.kr(carrier, 0.05);
    burst = p[4];

    // === INTERFERENCE (radio static) ===
    // Classic radio static with varying density
    intNoise = WhiteNoise.ar;
    intMod = LFNoise2.kr(2).range(0.5, 1.5);
    interferenceSig = BPF.ar(intNoise, 2000 * intMod, 0.5);
    interferenceSig = interferenceSig + (HPF.ar(intNoise, 4000) * 0.3);
    // Crackle component
    interferenceSig = interferenceSig + (Crackle.ar(1.8) * 0.2);
    // Varying intensity
    interferenceSig = interferenceSig * LFNoise1.kr(3).range(0.3, 1);
    interferenceSig = interferenceSig * interference * 0.4;

    // === GHOST (signal fragments) ===
    // Brief glimpses of signals
    ghostGate = LFNoise0.kr(3 + (ghost * 5)).range(0, 1) > 0.7;
    ghostMod = LFNoise0.kr(5).range(0.5, 2);
    ghostOsc = SinOsc.ar(freq * 2 * ghostMod) * ghostGate;
    // Add voice-like modulation
    ghostOsc = ghostOsc * (1 + (SinOsc.kr(LFNoise0.kr(2).range(3, 8)) * 0.3));
    // Occasional "words"
    ghostOsc = ghostOsc + (
        BPF.ar(PinkNoise.ar, 1000 * LFNoise2.kr(1).range(0.8, 1.2), 0.2) *
        LFNoise1.kr(4).range(0, 1) * ghostGate * 0.5
    );
    ghostSig = ghostOsc * ghost * 0.4;

    // === DEGRADE (bitcrushed decay) ===
    // Sample rate reduction suggesting failing digital
    degradeOsc = SinOsc.ar(freq);
    degradeOsc = degradeOsc + (Saw.ar(freq * 0.5) * 0.3);
    // Reduce sample rate based on degrade amount
    degradeBits = (1 - degrade).linexp(0, 1, 500, 44100);
    degradeOsc = Latch.ar(degradeOsc, Impulse.ar(degradeBits));
    // Add digital artifacts
    degradeOsc = degradeOsc + (
        LFPulse.ar(freq * 4, 0, LFNoise0.kr(10).range(0.1, 0.9)) *
        LFNoise0.kr(5).range(0, 0.3)
    );
    degradeSig = degradeOsc * degrade * 0.3;

    // === CARRIER (underlying tone) ===
    // Steady carrier wave with slight instability
    carrierMod = LFNoise2.kr(0.5).range(0.999, 1.001);
    carrierOsc = SinOsc.ar(freq * carrierMod);
    // AM modulation
    carrierOsc = carrierOsc * (1 + (SinOsc.kr(0.3).range(-0.1, 0.1)));
    // Slight harmonic content
    carrierOsc = carrierOsc + (SinOsc.ar(freq * 2 * carrierMod) * 0.2);
    carrierSig = carrierOsc * carrier * 0.3;

    // === BURST (EMF events) ===
    // Sudden electromagnetic burst
    burstTrig = Dust.ar(burst * 4);
    burstOsc = WhiteNoise.ar * EnvGen.ar(Env.perc(0.001, 0.1), burstTrig);
    // Add tonal component
    burstOsc = burstOsc + (
        SinOsc.ar(freq * 8 * TRand.ar(0.5, 2, burstTrig)) *
        EnvGen.ar(Env.perc(0.001, 0.05), burstTrig) * 0.5
    );
    // Zap character
    burstOsc = burstOsc + (
        SinOsc.ar(freq * 16 * EnvGen.ar(Env.perc(0.001, 0.02), burstTrig).linexp(0, 1, 0.5, 2)) *
        EnvGen.ar(Env.perc(0.001, 0.03), burstTrig) * 0.4
    );
    burstSig = HPF.ar(burstOsc, 500) * burst * 0.5;

    // === MIX ===
    sig = interferenceSig + ghostSig + degradeSig + carrierSig + burstSig;

    // Soft limiting
    sig = sig.tanh;

    sig = ~stereoSpread.(sig, 0.2, 0.3);  // Wide and jittery
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] static loaded".postln;
