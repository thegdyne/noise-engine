// seagrass_bay/grass_sway — Lightweight end-stage generator
SynthDef(\forge_seagrass_bay_grass_sway, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var sway, density, green, current, root;
    var blades, swayRate, currentMod, rootOsc;

    // Standard bus reads
    freq = In.kr(freqBus);

    sway = p[0];  // Undulation rate
    density = p[1];  // Number of grass blades
    green = p[2];  // Brightness
    current = p[3];  // Water flow mod
    root = p[4];  // Low anchor

    // Sway rate
    swayRate = sway.linexp(0, 1, 0.05, 0.8);

    // Current adds random drift
    currentMod = LFNoise1.kr(0.2) * current * 0.015;

    // Multiple detuned "blades" swaying at different phases
    blades = Mix.fill(6, { |i|
        var detune, phase, swayMod, blade;
        detune = (i - 2.5) * density.linlin(0, 1, 0.002, 0.008);
        phase = i * 0.5;
        swayMod = SinOsc.kr(swayRate, phase) * 0.01 * sway;
        blade = Pulse.ar(
            freq * (1 + detune + swayMod + currentMod),
            0.3 + (SinOsc.kr(swayRate * 0.7, phase) * 0.15)
        );
        blade * (1 / 6);
    });

    // Green = brightness/harmonics
    sig = LPF.ar(blades, green.linexp(0, 1, 1500, 6000));

    // Root - sub oscillator anchor
    rootOsc = SinOsc.ar(freq * 0.5) * root * 0.4;
    sig = sig + rootOsc;

    // Gentle stereo

    // Standard output chain
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_seagrass_bay_grass_sway loaded".postln;
