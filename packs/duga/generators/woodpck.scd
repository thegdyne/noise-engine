// duga/woodpck — Lightweight end-stage generator
SynthDef(\forge_duga_woodpck, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var rate, sharp, band, noise, drift;
    var tapRate, tapSig, noiseSig, driftMod, pulseWidth;

    freq = In.kr(freqBus);

    rate = p[0];
    sharp = p[1];
    band = p[2];
    noise = p[3];
    drift = p[4];

    // Tap rate - classic woodpecker was ~10Hz
    tapRate = rate.linexp(0, 1, 5, 20);
    driftMod = LFNoise2.kr(0.2).range(1 - (drift * 0.1), 1 + (drift * 0.1));
    tapRate = tapRate * driftMod;

    // Pulse width based on sharpness
    pulseWidth = sharp.linlin(0, 1, 0.3, 0.05);

    // The tapping signal - boosted
    tapSig = LFPulse.ar(tapRate, 0, pulseWidth);
    tapSig = tapSig * BPF.ar(WhiteNoise.ar(1), freq * driftMod, band.linexp(0, 1, 0.5, 0.05));
    tapSig = tapSig * 2;

    // Background shortwave static - continuous and louder
    noiseSig = BPF.ar(PinkNoise.ar(1), freq * 0.5, 0.3);
    noiseSig = noiseSig + (PinkNoise.ar(0.1)); // Continuous bed
    noiseSig = noiseSig * (0.3 + (noise * 0.4));

    // Mix
    sig = tapSig + noiseSig;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_duga_woodpck loaded".postln;
