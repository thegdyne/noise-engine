// seagrass_bay/current_drift — Lightweight end-stage generator
SynthDef(\forge_seagrass_bay_current_drift, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var flow, width, tumble, pressure, eddy;
    var noiseBase, flowMod, tumbleMod, pressureWave, eddySwirl, sigL, sigR;

    // Standard bus reads
    freq = In.kr(freqBus);

    flow = p[0];  // Current rate
    width = p[1];  // Stereo width
    tumble = p[2];  // Turbulence
    pressure = p[3];  // Pressure waves
    eddy = p[4];  // Swirling motion

    // Base noise - mix of pink (low rumble) and brown (very low)
    noiseBase = (PinkNoise.ar * 0.7) + (BrownNoise.ar * 0.3);

    // Flow modulation - slow sweeping filter
    flowMod = LFTri.kr(flow.linexp(0, 1, 0.05, 0.5)).range(0.3, 1);
    noiseBase = LPF.ar(noiseBase, freq * flowMod * 2);

    // Tumble - irregular bursts
    tumbleMod = LFNoise1.kr(tumble.linexp(0, 1, 0.5, 4)).range(0.5, 1);
    noiseBase = noiseBase * (1 - (tumble * 0.3) + (tumbleMod * tumble * 0.3));

    // Pressure waves - low frequency amplitude modulation
    pressureWave = SinOsc.kr(pressure.linexp(0, 1, 0.1, 0.8)).range(1 - (pressure * 0.2), 1);
    noiseBase = noiseBase * pressureWave;

    // Resonant peak at freq for tonal quality
    sig = BPF.ar(noiseBase, freq, 0.5) * 2;
    sig = sig + (noiseBase * 0.3);

    // Eddy - swirling stereo effect
    eddySwirl = LFTri.kr(eddy.linexp(0, 1, 0.1, 0.6));
    sigL = sig * (1 + (eddySwirl * eddy * 0.3));
    sigR = sig * (1 - (eddySwirl * eddy * 0.3));

    // Width control
    sig = [sigL, sigR];
    sig = (sig * width) + (Mix(sig) * (1 - width) * 0.5);

    // Standard output chain
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_seagrass_bay_current_drift loaded".postln;
