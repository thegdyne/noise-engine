// q121/gauge — Lightweight end-stage generator
SynthDef(\forge_q121_gauge, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var index, drift, hiss, click, ratio;
    var fmCarrier, fmMod, modFreq, modIndex, driftMod, hissNoise, clickTrig, clickSig;

    index = p[0];
    drift = p[1];
    hiss = p[2];
    click = p[3];
    ratio = p[4];

    freq = In.kr(freqBus);

    // Calibration drift - slow random frequency wobble
    driftMod = LFNoise1.kr(drift.linexp(0, 1, 0.1, 1)).range(0.99, 1.01);

    // FM synthesis - electronic tone
    modFreq = freq * ratio.linexp(0, 1, 1, 8) * driftMod;
    modIndex = index.linexp(0, 1, 0.5, 12);
    fmMod = SinOsc.ar(modFreq) * modIndex * modFreq;
    fmCarrier = SinOsc.ar((freq * driftMod) + fmMod) * 0.4;

    // Add harmonics for electronic character
    fmCarrier = fmCarrier + (SinOsc.ar(freq * 2 * driftMod + (fmMod * 0.5)) * 0.15);
    fmCarrier = fmCarrier + (SinOsc.ar(freq * 3 * driftMod + (fmMod * 0.3)) * 0.08);

    // Electronic hiss - high frequency noise
    hissNoise = HPF.ar(WhiteNoise.ar(0.1), 6000) * hiss;
    hissNoise = hissNoise + (HPF.ar(PinkNoise.ar(0.08), 4000) * hiss);

    // Relay clicks - sparse impulsive sounds
    clickTrig = Dust.ar(click.linexp(0, 1, 0.5, 8));
    clickSig = Ringz.ar(clickTrig, freq * 4, 0.01) * 0.3;
    clickSig = clickSig + (Ringz.ar(clickTrig, freq * 6, 0.008) * 0.2);

    // Mix
    sig = fmCarrier + hissNoise + clickSig;

    // Continuous bed for drone stability
    sig = sig + (BPF.ar(PinkNoise.ar(0.03), freq * 2, 0.5));

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_q121_gauge loaded".postln;
