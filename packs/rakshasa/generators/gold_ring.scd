// rakshasa/gold_ring — Lightweight end-stage generator
// Gold Ring -- Metallic ring modulation with pendulum swing
// Role: motion | Family: physical

SynthDef(\forge_rakshasa_gold_ring, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var metal, shine, swing, clang, chain;
    var carrier, modulator, ringMod, shimmer, swingMod;
    var clangEnv, resonance;

    // Standard bus reads
    freq = In.kr(freqBus);

    // Custom parameters
    metal = p[0].linlin(0, 1, 0, 1);  // Ring mod mix
    shine = p[1].linexp(0, 1, 1, 4);  // Brightness/harmonics
    swing = p[2].linexp(0, 1, 0.2, 5);  // Pendulum rate
    clang = p[3].linexp(0, 1, 0.01, 0.001);  // Attack sharpness
    chain = p[4].linlin(0, 1, 0.9, 0.998);  // Resonance/sustain

    // Swing modulation -- pendulum movement
    swingMod = SinOsc.kr(swing).range(0.95, 1.05);

    // Carrier -- clean tone
    carrier = SinOsc.ar(freq * swingMod);

    // Modulator for ring mod -- inharmonic ratio for metal
    modulator = SinOsc.ar(freq * 1.414 * swingMod);  // sqrt(2) for metallic

    // Ring modulation
    ringMod = carrier * modulator;

    // Mix clean and ring mod based on metal
    sig = (carrier * (1 - metal)) + (ringMod * metal);

    // Shimmer -- high harmonics for gold shine
    shimmer = SinOsc.ar(freq * shine * swingMod) * 0.2;
    shimmer = shimmer + (SinOsc.ar(freq * shine * 1.5 * swingMod) * 0.1);
    sig = sig + (shimmer * shine.linlin(1, 4, 0, 0.5));

    // Resonant ringing with feedback for chain
    resonance = CombL.ar(sig, 0.1, 1/freq, decay * chain.linlin(0.9, 0.998, 0.5, 4));
    sig = sig + (resonance * chain.linlin(0.9, 0.998, 0, 0.4));

    // Stereo swing
    sig = Pan2.ar(sig, SinOsc.kr(swing * 0.7).range(-0.5, 0.5));

                   clockTrigBus, midiTrigBus, slotIndex);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  * forge_rakshasa_gold_ring loaded".postln;
