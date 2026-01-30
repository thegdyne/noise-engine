// seagrass_bay/crystal_spring — Lightweight end-stage generator
SynthDef(\forge_seagrass_bay_crystal_spring, { |out, freqBus, customBus0|
    var sig, trig, freq, neArr, ne_cut, ne_rq, ne_lp, ne_hp, ne_bp, ne_nt, ne_lp2, ne_off, ne_env, ne_pan, ne_panRate, ne_panWidth, ne_atkT, ne_relT;
    var p = In.kr(customBus0, 5);
    var clarity, shimmer, flow, cold, light;
    var fundamental, partials, flowMod, lightSparkle;
    // @forge: inline_post_chain

    // Standard bus reads
    freq = In.kr(freqBus);
    amp = 0.2;

    clarity = p[0];  // Purity
    shimmer = p[1];  // Sparkle
    flow = p[2];  // Water movement
    cold = p[3];  // Brightness
    light = p[4];  // Sunlight sparkle

    // Flow modulation - gentle pitch/amplitude ripple
    flowMod = SinOsc.kr(flow.linexp(0, 1, 0.3, 2)) * flow * 0.005;
    freq = freq * (1 + flowMod);

    // Fundamental - pure sine for clarity
    fundamental = SinOsc.ar(freq) * clarity.linlin(0, 1, 0.4, 0.7);

    // Bell-like partials (slightly inharmonic for realism)
    partials = Mix.fill(6, { |i|
        var ratio, partial, partialAmp;
        ratio = [1, 2.0, 3.01, 4.02, 5.04, 6.08][i];
        partialAmp = (1 / (i + 1).squared) * shimmer;
        // Cold shifts partials brighter
        partial = SinOsc.ar(freq * ratio * (1 + (cold * 0.02 * i)));
        partial * partialAmp;
    });

    sig = fundamental + (partials * 0.6);

    // Light sparkle - high frequency shimmer
    lightSparkle = Ringz.ar(
        Dust.ar(light.linexp(0, 1, 2, 20)),
        freq * [4, 5, 6].choose,
        0.1
    ) * light * 0.15;
    sig = sig + lightSparkle;

    // Cold = high shelf boost
    sig = BHiShelf.ar(sig, 3000, 1, cold * 6);
    // Shimmer stereo spread
    ne_panRate  = shimmer.linexp(0, 1, 0.05, 0.8);
    ne_panWidth = shimmer.linlin(0, 1, 0.2, 0.8);
    sig = Pan2.ar(Mix(sig), SinOsc.kr(ne_panRate).range(ne_panWidth.neg, ne_panWidth), 0.4);

    // Standard output chain
    neArr = sig.asArray;
    if(neArr.size == 1, { sig = [neArr[0], neArr[0]] }, { sig = neArr });

    // Filter select: 0=LP 1=HP 2=BP 3=Notch 4=LP2 5=OFF
    ne_cut = filterFreq.clip(20, 18000);
    ne_rq = rq.clip(0.05, 2);
    ne_lp = RLPF.ar(sig, ne_cut, ne_rq);
    ne_hp = RHPF.ar(sig, ne_cut, ne_rq);
    ne_bp = BPF.ar(sig, ne_cut, ne_rq);
    ne_nt = BRF.ar(sig, ne_cut, ne_rq);
    ne_lp2 = RLPF.ar(ne_lp, ne_cut, ne_rq);
    ne_off = sig;
    sig = Select.ar(filterType.round.clip(0, 5), [ne_lp, ne_hp, ne_bp, ne_nt, ne_lp2, ne_off]);

    // Env VCA (drone / clock / midi)
    ne_atkT = attack.linexp(0, 1, 0.001, 2);
    ne_relT = decay.linexp(0, 1, 0.05, 4);
    trig = Select.kr(envSource.round.clip(0, 2), [
        0,
        Select.kr(clockRate.round.clip(0, 12), In.kr(clockTrigBus, 13)),
        Select.kr(slotIndex.clip(0, 7), In.kr(midiTrigBus, 8))
    ]);
    ne_env = Select.kr(envSource.round.clip(0, 2), [
        1.0,
        Decay2.kr(trig, ne_atkT, ne_relT),
        Decay2.kr(trig, ne_atkT, ne_relT)
    ]);
    sig = sig * ne_env * amp;

    // Ensure 2ch
    neArr = sig.asArray;
    if(neArr.size == 1, { sig = [neArr[0], neArr[0]] }, { sig = neArr });
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_seagrass_bay_crystal_spring loaded".postln;
