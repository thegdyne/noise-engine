// aurora_cave/boreal — Lightweight end-stage generator
SynthDef(\forge_aurora_cave_boreal, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var flow, curtain, pulse, color, vast;
    var layers, flowMod, pulseMod, colorMix;

    freq = In.kr(freqBus);

    flow = p[0];
    curtain = p[1];
    pulse = p[2];
    color = p[3];
    vast = p[4];

    // Flow modulation - aurora drift
    flowMod = LFNoise2.kr(flow.linexp(0, 1, 0.02, 0.3));

    // Pulse modulation - brightness waves
    pulseMod = SinOsc.kr(pulse.linexp(0, 1, 0.05, 0.5)).range(0.5, 1) ** 2;

    // Build spectral layers - aurora curtains
    layers = Array.fill(8, { |i|
        var harmonic = i + 1;
        var layerFreq = freq * harmonic * (1 + (flowMod * 0.02 * harmonic));
        var oddEven = (harmonic.odd).if(1, color);
        var layerAmp = oddEven / (harmonic ** 0.7);
        var drift = LFNoise2.kr(flow.linexp(0, 1, 0.05, 0.4) * (1 + (i * 0.1)));
        var layerPulse = SinOsc.kr(
            pulse.linexp(0, 1, 0.03, 0.3) * (1 + (i * 0.05)),
            i * 0.3
        ).range(0.4, 1);

        SinOsc.ar(layerFreq * (1 + (drift * 0.01))) * layerAmp * layerPulse * (i < (curtain * 8 + 2)).if(1, 0)
    }).sum;

    // Higher ethereal layer
    layers = layers + Array.fill(4, { |i|
        var highHarm = [9, 11, 13, 15][i];
        var highAmp = 0.1 / highHarm;
        var highDrift = LFNoise2.kr(flow.linexp(0, 1, 0.1, 0.6));
        SinOsc.ar(freq * highHarm * (1 + (highDrift * 0.02))) * highAmp * curtain * pulseMod
    }).sum;

    sig = layers * 0.25;

    // Apply overall pulse
    sig = sig * pulseMod.sqrt;

    // Soft saturation for glow
    sig = (sig * 1.5).tanh * 0.8;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_aurora_cave_boreal loaded".postln;
