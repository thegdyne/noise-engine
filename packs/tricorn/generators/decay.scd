// tricorn/decay — Lightweight end-stage generator
SynthDef(\forge_tricorn_decay, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var erosion, crumble, stain, moss, fracture;
    var source, crushed, bits, sampleRate, stainMod, glitch;

    erosion = p[0];
    crumble = p[1];
    stain = p[2];
    moss = p[3];
    fracture = p[4];

    freq = In.kr(freqBus);

    // Source - oscillator + noise mix
    source = Saw.ar(freq, 0.3);
    source = source + Pulse.ar(freq * 0.5, 0.4, 0.2);
    source = source + (PinkNoise.ar(0.2) * moss);

    // Moss - organic texture layer
    source = source + (LFNoise1.ar(freq * 0.1, 0.15) * moss);

    // Stain modulation - wandering filter
    stainMod = LFNoise2.kr(0.3 + (stain * 0.5)).range(0.5, 2.0);
    source = BPF.ar(source, freq * stainMod, 0.5 + (stain * 0.4)) * 2;
    source = source + (BrownNoise.ar(0.1) * stain);

    // Bit depth reduction (erosion)
    bits = erosion.linexp(0, 1, 16, 3);
    crushed = source.round(2.pow(bits.neg));

    // Sample rate reduction (crumble)
    sampleRate = crumble.linexp(0, 1, 44100, 2000);
    crushed = Latch.ar(crushed, Impulse.ar(sampleRate));

    // Blend original with crushed
    sig = (source * (1 - (erosion * 0.7))) + (crushed * erosion * 0.8);

    // Fracture glitches - sample and hold stutters
    glitch = Latch.ar(sig, Dust.ar(fracture.linexp(0, 1, 1, 50)));
    sig = Select.ar(LFPulse.kr(fracture.linexp(0, 1, 0.5, 8), 0, fracture * 0.3), [sig, glitch]);

    // Add continuous noise bed for presence
    sig = sig + (PinkNoise.ar(0.05));

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_tricorn_decay loaded".postln;
