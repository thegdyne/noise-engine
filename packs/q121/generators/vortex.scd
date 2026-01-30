// q121/vortex — Lightweight end-stage generator
SynthDef(\forge_q121_vortex, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var turb, spin, chaos, core, shed;
    var chaosOsc, turbLayer, coreOsc, shedTrig, spinMod;

    turb = p[0];
    spin = p[1];
    chaos = p[2];
    core = p[3];
    shed = p[4];

    freq = In.kr(freqBus);

    // Spin modulation - rotation creates pitch wobble
    spinMod = SinOsc.kr(spin.linexp(0, 1, 0.2, 8), [0, 0.5pi]).range(0.95, 1.05);

    // Chaos oscillators - Lorenz-like behavior via coupled modulators
    chaosOsc = Crackle.ar(chaos.linlin(0, 1, 1.5, 1.99)) * 0.3;
    chaosOsc = chaosOsc + (LFNoise0.ar(freq * chaos.linexp(0, 1, 0.5, 4)) * 0.2);
    chaosOsc = BPF.ar(chaosOsc, freq * spinMod, turb.linlin(0, 1, 0.5, 0.15)) * 3;

    // Turbulence layer - filtered noise swells
    turbLayer = BPF.ar(PinkNoise.ar(1), freq * 2 * spinMod, 0.3) * turb;
    turbLayer = turbLayer * LFNoise2.kr(spin.linexp(0, 1, 1, 10)).range(0.3, 1);

    // Vortex core - low resonant tone
    coreOsc = SinOsc.ar(freq * 0.5 * spinMod) * core * 0.4;
    coreOsc = coreOsc + (SinOsc.ar(freq * spinMod) * core * 0.2);
    coreOsc = coreOsc * LFNoise2.kr(0.5).range(0.7, 1);

    // Vortex shedding - quasi-periodic bursts
    shedTrig = Dust.ar(shed.linexp(0, 1, 2, 30));
    sig = chaosOsc + turbLayer + coreOsc;
    sig = sig + (Ringz.ar(shedTrig, freq * 3, 0.05) * shed * 0.3);

    // Continuous noise bed for drone stability
    sig = sig + (BrownNoise.ar(0.05) * turb);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_q121_vortex loaded".postln;
