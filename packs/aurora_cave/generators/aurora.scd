SynthDef(\forge_aurora_cave_aurora, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                        filterTypeBus, envEnabledBus, envSourceBus=0,
                                        clockRateBus, clockTrigBus,
                                        midiTrigBus=0, slotIndex=0,
                                        customBus0, customBus1, customBus2, customBus3, customBus4,
                                     portamentoBus|

    var sig, trig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento, neArr, ne_cut, ne_rq, ne_lp, ne_hp, ne_bp, ne_nt, ne_lp2, ne_off, ne_env, ne_pan, ne_panRate, ne_panWidth, ne_atkT, ne_relT;
    var shimmer, bands, drift, glow, spread;
    var harmonics, driftMod;
    // @forge: inline_post_chain
    freq = In.kr(freqBus);
    portamento = In.kr(portamentoBus);
    freq = Lag.kr(freq, portamento.linexp(0, 1, 0.001, 0.5));
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    amp = 0.2;

    shimmer = In.kr(customBus0);
    bands = In.kr(customBus1);
    drift = In.kr(customBus2);
    glow = In.kr(customBus3);
    spread = In.kr(customBus4);

    driftMod = LFNoise2.kr(drift.linexp(0, 1, 0.05, 0.5));

    // Fixed 8 harmonics, bands controls amplitude rolloff
    harmonics = SinOsc.ar(freq * (1 + (driftMod * 0.02))) * 1.0 *
        SinOsc.kr(shimmer.linexp(0, 1, 0.1, 3), 0).range(0.3, 1);
    harmonics = harmonics + (SinOsc.ar(freq * 2 * (1 + (driftMod * 0.04))) * (0.7 * bands.linlin(0, 1, 0.3, 1)) *
        SinOsc.kr(shimmer.linexp(0, 1, 0.1, 3) * 1.1, 0.5).range(0.3, 1));
    harmonics = harmonics + (SinOsc.ar(freq * 3 * (1 + (driftMod * 0.06))) * (0.55 * bands.linlin(0, 1, 0.2, 1)) *
        SinOsc.kr(shimmer.linexp(0, 1, 0.1, 3) * 1.2, 1.0).range(0.3, 1));
    harmonics = harmonics + (SinOsc.ar(freq * 4 * (1 + (driftMod * 0.08))) * (0.45 * bands.linlin(0, 1, 0.1, 1)) *
        SinOsc.kr(shimmer.linexp(0, 1, 0.1, 3) * 1.3, 1.5).range(0.3, 1));
    harmonics = harmonics + (SinOsc.ar(freq * 5 * (1 + (driftMod * 0.1))) * (0.35 * bands) *
        SinOsc.kr(shimmer.linexp(0, 1, 0.1, 3) * 1.4, 2.0).range(0.3, 1));
    harmonics = harmonics + (SinOsc.ar(freq * 6 * (1 + (driftMod * 0.12))) * (0.25 * bands) *
        SinOsc.kr(shimmer.linexp(0, 1, 0.1, 3) * 1.5, 2.5).range(0.3, 1));
    harmonics = harmonics + (SinOsc.ar(freq * 7 * (1 + (driftMod * 0.14))) * (0.18 * bands) *
        LFNoise2.kr(shimmer.linexp(0, 1, 0.2, 2)).range(0, 0.15));
    harmonics = harmonics + (SinOsc.ar(freq * 8 * (1 + (driftMod * 0.16))) * (0.12 * bands) *
        LFNoise2.kr(shimmer.linexp(0, 1, 0.15, 1.5)).range(0, 0.1));

    sig = harmonics * 0.2;
    sig = (sig * (1 + (glow * 2))).tanh * (1 - (glow * 0.3));
    // Output chain (inlined; avoids global helpers for NRT stability)
    sig = LeakDC.ar(sig);
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
    Out.ar(out, sig);
}).add;
"  * forge_aurora_cave_aurora loaded".postln;
