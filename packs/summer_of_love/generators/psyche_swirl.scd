// summer_of_love/psyche_swirl — Lightweight end-stage generator
SynthDef(\forge_summer_of_love_psyche_swirl, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var spin, depth, spiral, kaleid, cosmos;
    var spinRate, phases, phaseMod, voices, folded, smear;

    freq = In.kr(freqBus);

    spin = p[0];  // Rotation speed
    depth = p[1];  // Modulation depth
    spiral = p[2];  // Complexity
    kaleid = p[3];  // Wavefolding
    cosmos = p[4];  // Reverb smear

    // Spin rate - from very slow to medium-fast
    spinRate = spin.linexp(0, 1, 0.05, 4);

    // Phase offsets for quadrature-style rotation
    phases = [0, 0.25, 0.5, 0.75];

    // Create rotating phase-modulated voices
    voices = phases.collect({ |phaseOff, i|
        var lfo, modSig, carrier, pan;
        var spiralLfo;

        // Main rotation LFO with phase offset
        lfo = SinOsc.kr(spinRate, phaseOff * 2pi);

        // Spiral adds secondary modulation
        spiralLfo = SinOsc.kr(spinRate * (2 + i), phaseOff * 2pi) * spiral * 0.5;

        // Phase modulation signal
        modSig = SinOsc.ar(freq * (1 + (i * 0.002))) * (depth * 4 + (spiralLfo * depth * 2));

        // Carrier with phase modulation
        carrier = SinOsc.ar(freq * (1 + (i * 0.001)), modSig);

        // Add some harmonics for richness
        carrier = carrier + (SinOsc.ar(freq * 2 * (1 + (i * 0.002)), modSig * 1.5) * 0.3);
        carrier = carrier + (SinOsc.ar(freq * 3 * (1 + (i * 0.003)), modSig * 2) * 0.15 * spiral);

        // Pan based on LFO for rotation
        pan = lfo;
        Pan2.ar(carrier, pan)
    }).sum;

    sig = voices * 0.35;

    // Kaleidoscope - wavefolding for harmonic complexity
    folded = sig.fold2(1 - (kaleid * 0.5));
    sig = XFade2.ar(sig, folded, kaleid.linlin(0, 1, -1, 0.5));

    // Cosmos - smeared reverb-like tail using allpass delays
    smear = sig;
    4.do({ |i|
        smear = AllpassL.ar(smear, 0.2, (0.03 + (i * 0.017)).clip(0.01, 0.2), cosmos * 2);
    });
    sig = sig + (smear * cosmos * 0.5);

    // Apply standard processing chain

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_summer_of_love_psyche_swirl loaded".postln;
