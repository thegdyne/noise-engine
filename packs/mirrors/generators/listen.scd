// mirrors/listen — Lightweight end-stage generator
SynthDef(\forge_mirrors_listen, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var scan, focusAmt, breath, strain, silence;
    var grains, grainRate, trig1, trig2, trig3;
    var breathNoise, strainTone, silenceFloor;

    scan = p[0];
    focusAmt = p[1];
    breath = p[2];
    strain = p[3];
    silence = p[4];

    freq = In.kr(freqBus);

    // Grain rate based on scanning
    grainRate = scan.linexp(0, 1, 5, 40);

    // Multiple grain streams
    trig1 = Dust.ar(grainRate);
    trig2 = Dust.ar(grainRate * 0.6);
    trig3 = Dust.ar(grainRate * 1.2);

    // Grains - soft focused sounds from distance
    grains = Ringz.ar(trig1, freq * LFNoise2.kr(0.3).range(0.95, 1.05), 0.06 + (focusAmt * 0.08), 0.2);
    grains = grains + Ringz.ar(trig2, freq * 1.5, 0.05 + (focusAmt * 0.06), 0.15);
    grains = grains + Ringz.ar(trig3, freq * 0.75, 0.08, 0.18);
    grains = grains + Ringz.ar(trig1, freq * 2, 0.04, 0.12 * focusAmt);

    // Soft envelope on grains
    grains = LPF.ar(grains, focusAmt.linexp(0, 1, 1500, 4000));

    sig = grains * 0.5;

    // Operator breath - low filtered noise
    breathNoise = LPF.ar(PinkNoise.ar(0.25), 400);
    breathNoise = breathNoise * SinOsc.kr(breath.linexp(0, 1, 0.15, 0.4)).range(0.6, 1.0);
    sig = sig + (breathNoise * breath);

    // Listening strain - high tension tone
    strainTone = SinOsc.ar(freq * 4, 0, 0.06 * strain);
    strainTone = strainTone * LFNoise2.kr(2).range(0.5, 1.0);
    sig = sig + strainTone;

    // Waiting silence floor
    silenceFloor = HPF.ar(PinkNoise.ar(0.12), 1000);
    silenceFloor = silenceFloor * LFNoise2.kr(0.3).range(0.4, 1.0);
    sig = sig + (silenceFloor * silence * 0.5);

    // Pitched listening tone
    sig = sig + BPF.ar(PinkNoise.ar(0.15), freq, 0.35) * 2;

    // Continuous bed
    sig = sig + LPF.ar(BrownNoise.ar(0.1), 300);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_mirrors_listen loaded".postln;
