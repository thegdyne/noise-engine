SynthDef(\forge_moss_root_leaf_fall, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                        filterTypeBus, envEnabledBus, envSourceBus=0,
                                        clockRateBus, clockTrigBus,
                                        midiTrigBus=0, slotIndex=0,
                                        customBus0, customBus1, customBus2, customBus3, customBus4,
                                     portamentoBus|

    var sig, trig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento, neArr, ne_cut, ne_rq, ne_lp, ne_hp, ne_bp, ne_nt, ne_lp2, ne_off, ne_env, ne_pan, ne_panRate, ne_panWidth, ne_atkT, ne_relT;
    var rustle, wind, wet, pile, curl;
    var leaves, crunch, pileDelay;

    // Standard reads
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

    // Custom params
    rustle = In.kr(customBus0);
    wind = In.kr(customBus1);
    wet = In.kr(customBus2);
    pile = In.kr(customBus3);
    curl = In.kr(customBus4);

    // Multiple rustling layers
    leaves = Mix(Array.fill(4, { |i|
        var rate = wind.linexp(0, 1, 2, 20) * (1 + (i * 0.3));
        var noiseFreq = freq * (2 + i);
        var ampMod = LFNoise2.kr(rate).range(0, 1);
        var layer = BPF.ar(
            WhiteNoise.ar,
            noiseFreq.clip(100, 10000),
            curl.linexp(0, 1, 0.5, 0.1)
        ) * ampMod;
        layer * (rustle / 4)
    }));

    // Crunch: high-frequency crackle
    crunch = HPF.ar(
        Dust2.ar(wind.linexp(0, 1, 50, 500) * rustle) * 0.3,
        curl.linexp(0, 1, 3000, 6000)
    ) * curl;

    sig = leaves + crunch;

    // Wetness: dampen high frequencies
    sig = LPF.ar(sig, wet.linexp(0, 1, 12000, 2000));
    sig = sig * wet.linlin(0, 1, 1, 0.6); // Wet leaves are quieter

    // Pile: multiple short delays for depth
    pileDelay = Mix([
        DelayL.ar(sig, 0.1, 0.02) * 0.3,
        DelayL.ar(sig, 0.1, 0.05) * 0.2,
        DelayL.ar(sig, 0.1, 0.08) * 0.15
    ]) * pile;
    sig = sig + pileDelay;

    // Stereo scatter
    sig = Pan2.ar(Mix(sig), SinOsc.kr(wind.linexp(0, 1, 0.2, 0.8).max(0.001)) * rustle.linlin(0, 1, 0.3, 0.8));

    // MANDATORY output chain
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
"  * forge_moss_root_leaf_fall loaded".postln;
