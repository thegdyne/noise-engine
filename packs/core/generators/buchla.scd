// core/buchla — Lightweight end-stage generator
/*
Buchla Generator
West Coast / Buchla-inspired synthesis

Features:
  - Complex oscillator with wavefolder
  - Variable symmetry (waveform morphing)
  - Internal modulation oscillator
  - LPG (Low-Pass Gate) with vactrol-style response
  - Chaotic modulation source

Custom params:
  - P1 timbre: Wavefolder intensity
  - P2 symmetry: Waveform symmetry (sine -> saw-like)
  - P3 modindex: Internal FM modulation depth
  - P4 lpg_decay: Low-pass gate decay time
  - P5 chaos: Chaotic modulation amount
*/

SynthDef(\buchla, { |out, freqBus, customBus0|
    var sig, freq;
    var p = In.kr(customBus0, 5);
    var timbre, symmetry, modindex, lpgDecay, chaos;
    var trig, complexOsc, modOsc, folded;
    var lpgEnv, lpgFreq, chaosLFO;

    freq = In.kr(freqBus);

    timbre = p[0];
    symmetry = p[1];
    modindex = p[2];
    lpgDecay = p[3];
    chaos = p[4];

    // One-shot trigger (end-stage handles retriggering)
    trig = Impulse.ar(0);

    // === CHAOS SOURCE ===
    chaosLFO = Crackle.ar(1.5 + (chaos * 0.4)) * chaos * 0.3;

    // === MODULATION OSCILLATOR ===
    modOsc = SinOsc.ar(freq * (1.5 + chaosLFO)) * modindex * freq;

    // === COMPLEX OSCILLATOR ===
    // Variable symmetry sine (morphs toward saw-like with asymmetry)
    complexOsc = SinOsc.ar(freq + modOsc, 0);

    // Add harmonics based on symmetry
    complexOsc = complexOsc + (SinOsc.ar((freq + modOsc) * 2) * symmetry * 0.3);
    complexOsc = complexOsc + (SinOsc.ar((freq + modOsc) * 3) * symmetry * 0.15);

    // === WAVEFOLDER ===
    // Classic Buchla-style wavefolding
    folded = complexOsc * (1 + (timbre * 8));
    folded = folded.fold(-1, 1);

    // Mix original and folded based on timbre
    sig = XFade2.ar(complexOsc, folded, timbre.linlin(0, 1, -1, 0.5));

    // === LOW-PASS GATE ===
    // Vactrol-style response: slow attack, variable decay
    // Both amplitude AND filter respond together
    lpgEnv = EnvGen.ar(
        Env.perc(0.01, lpgDecay, 1, -4),
        trig
    );

    // LPG filter frequency follows envelope
    lpgFreq = lpgEnv.linexp(0, 1, 100, 8000);

    // Apply LPG - filter + amplitude coupled
    sig = RLPF.ar(sig, lpgFreq, 0.5);
    sig = sig * lpgEnv;

    // === ADDITIONAL FILTERING ===
    // User filter on top of LPG

    // === OUTPUT ===
    sig = ~stereoSpread.(sig, 0.15, 0.3);
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] buchla loaded".postln;
