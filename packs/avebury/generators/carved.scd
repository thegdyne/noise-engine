// avebury/carved — Lightweight end-stage generator
SynthDef(\forge_avebury_carved, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var marks, depthParam, bark, letter, memory;
    var trig, resonances, barkNoise, decayTime, scrapes;

    marks = p[0];
    depthParam = p[1];
    bark = p[2];
    letter = p[3];
    memory = p[4];

    freq = In.kr(freqBus);

    // Carving trigger rate
    trig = Dust.ar(marks.linexp(0, 1, 2, 25));

    // Decay time for memory
    decayTime = memory.linexp(0, 1, 0.1, 0.8);

    // Resonances - carved letter shapes at varying pitches
    resonances = Ringz.ar(trig, freq * (1 + (LFNoise0.kr(3) * letter * 0.3)), decayTime, 0.25 * depthParam);
    resonances = resonances + Ringz.ar(trig, freq * 2 * (1 + (LFNoise0.kr(2) * letter * 0.2)), decayTime * 0.6, 0.2 * depthParam);
    resonances = resonances + Ringz.ar(trig, freq * 0.5, decayTime * 1.2, 0.2 * depthParam);
    resonances = resonances + Ringz.ar(trig, freq * 3 * (1 + (LFNoise0.kr(4) * letter * 0.15)), decayTime * 0.4, 0.15 * depthParam);

    sig = resonances;

    // Bark surface texture - continuous crackle (always present)
    barkNoise = Crackle.ar(1.6 + (bark * 0.3), 0.2 + (bark * 0.15));
    barkNoise = BPF.ar(barkNoise, freq * 1.5, 0.5) * 2;
    sig = sig + barkNoise;

    // Scrape transients
    scrapes = HPF.ar(PinkNoise.ar(0.3) * Decay.ar(trig, 0.03), 3000);
    sig = sig + (scrapes * marks * 0.4);

    // Strong continuous bed for drone safety
    sig = sig + LPF.ar(PinkNoise.ar(0.25), 600);
    sig = sig + BPF.ar(BrownNoise.ar(0.3), freq, 0.4) * 3;
    sig = sig + LPF.ar(BrownNoise.ar(0.15), 200);

    // Memory echo
    sig = sig + AllpassC.ar(sig, 0.5, memory.linlin(0, 1, 0.1, 0.35), memory * 2, 0.3);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_avebury_carved loaded".postln;
