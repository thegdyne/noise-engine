// tricorn/rubble — Lightweight end-stage generator
SynthDef(\forge_tricorn_rubble, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var impacts, chunks, scatter, settle, dustAmt;
    var trig, resonances, dustCloud, decayTime, freqSpread;

    impacts = p[0];
    chunks = p[1];
    scatter = p[2];
    settle = p[3];
    dustAmt = p[4];

    freq = In.kr(freqBus);

    // Trigger rate based on impacts
    trig = Dust.ar(impacts.linexp(0, 1, 1, 30));

    // Decay time based on settle
    decayTime = settle.linexp(0, 1, 0.05, 0.8);

    // Frequency spread based on chunks
    freqSpread = chunks.linlin(0, 1, 0.5, 3);

    // Multiple resonances for different debris sizes
    // Small debris - high freq
    resonances = Ringz.ar(trig, freq * (2 + (LFNoise0.kr(5) * scatter)), decayTime * 0.3, 0.2);
    resonances = resonances + Ringz.ar(trig, freq * (3 + (LFNoise0.kr(4) * scatter * freqSpread)), decayTime * 0.2, 0.15);

    // Medium chunks
    resonances = resonances + Ringz.ar(trig, freq * (1 + (LFNoise0.kr(3) * scatter * 0.5)), decayTime * 0.6, 0.25);
    resonances = resonances + Ringz.ar(trig, freq * (1.5 + (LFNoise0.kr(2) * scatter)), decayTime * 0.5, 0.2);

    // Large pieces - low freq
    resonances = resonances + Ringz.ar(trig, freq * (0.5 + (LFNoise0.kr(1) * scatter * 0.3)), decayTime, 0.3);
    resonances = resonances + Ringz.ar(trig, freq * 0.25, decayTime * 1.2, 0.2 * (1 - chunks));

    sig = resonances * 0.5;

    // Dust cloud - continuous noise layer
    dustCloud = PinkNoise.ar(0.2) + BrownNoise.ar(0.15);
    dustCloud = LPF.ar(dustCloud, freq * 2);
    dustCloud = dustCloud * LFNoise2.kr(0.5).range(0.6, 1.0);

    sig = sig + (dustCloud * (0.3 + (dustAmt * 0.7)));

    // Continuous low rumble for drone safety - boosted
    sig = sig + LPF.ar(BrownNoise.ar(0.15), 200);
    sig = sig + LPF.ar(PinkNoise.ar(0.1), freq);

    // Impact transients - filtered noise bursts
    sig = sig + (HPF.ar(PinkNoise.ar(0.3) * Decay.ar(trig, 0.02), 2000) * impacts);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_tricorn_rubble loaded".postln;
