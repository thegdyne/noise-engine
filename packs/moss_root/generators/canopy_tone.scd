// moss_root/canopy_tone — Lightweight end-stage generator
SynthDef(\forge_moss_root_canopy_tone, { |out, freqBus, customBus0|

    var sig, trig, freq, neArr, ne_cut, ne_rq, ne_lp, ne_hp, ne_bp, ne_nt, ne_lp2, ne_off, ne_env, ne_pan, ne_panRate, ne_panWidth, ne_atkT, ne_relT;
    var p = In.kr(customBus0, 5);
    var glow, flutter, gaps, hue, air;
    var fmCarrier, fmMod, tremolo, gapMod, airNoise, warmth;
    // @forge: inline_post_chain

    freq = In.kr(freqBus);
    amp = 0.2;

    glow = p[0];
    flutter = p[1];
    gaps = p[2];
    hue = p[3];
    air = p[4];

    // FM synthesis for shimmering tones
    fmMod = SinOsc.ar(freq * 2) * glow.linlin(0, 1, 0.5, 3);
    fmCarrier = SinOsc.ar(freq + fmMod) * 0.5;

    // Add harmonics via additional FM layer
    fmCarrier = fmCarrier + (SinOsc.ar(freq * 1.5 + (SinOsc.ar(freq * 3) * glow)) * 0.2 * glow);

    // Flutter: tremolo from leaves
    tremolo = LFTri.kr(flutter.linexp(0, 1, 2, 12)).range(
        1 - (flutter * 0.4),
        1
    );

    // Gaps: irregular amplitude modulation
    gapMod = LFNoise1.kr(gaps.linexp(0, 1, 0.5, 4)).range(
        1 - gaps,
        1
    );

    sig = fmCarrier * tremolo * gapMod;

    // Air: high frequency breath
    airNoise = HPF.ar(PinkNoise.ar, 6000) * air * 0.15;
    airNoise = airNoise * LFNoise2.kr(3).range(0.5, 1);
    sig = sig + airNoise;

    // Hue: warmth filtering (low hue = cooler, high = warmer golden)
    warmth = hue.linexp(0, 1, 6000, 2500);
    sig = LPF.ar(sig, warmth);
    // Add subtle warmth harmonics
    sig = sig + (SinOsc.ar(freq * 0.5) * hue * 0.1);

    // Gentle stereo spread
    sig = Pan2.ar(Mix(sig), SinOsc.kr(flutter.linexp(0, 1, 0.1, 0.4).max(0.001)) * 0.4);

    // MANDATORY output chain
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
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);
    ne_env = Select.kr(envSource.round.clip(0, 2), [
        1.0,
        Decay2.kr(A2K.kr(trig), ne_atkT, ne_relT),
        Decay2.kr(A2K.kr(trig), ne_atkT, ne_relT)
    ]);
    sig = sig * ne_env * amp;

    // Ensure 2ch
    neArr = sig.asArray;
    if(neArr.size == 1, { sig = [neArr[0], neArr[0]] }, { sig = neArr });
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_moss_root_canopy_tone loaded".postln;
