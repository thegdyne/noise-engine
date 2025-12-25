SynthDef(\forge_moss_root_root_drone, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                          filterTypeBus, envEnabledBus, envSourceBus=0,
                                          clockRateBus, clockTrigBus,
                                          midiTrigBus=0, slotIndex=0,
                                          customBus0, customBus1, customBus2, customBus3, customBus4,
                                     portamentoBus|

    var sig, trig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento, neArr, ne_cut, ne_rq, ne_lp, ne_hp, ne_bp, ne_nt, ne_lp2, ne_off, ne_env, ne_pan, ne_panRate, ne_panWidth, ne_atkT, ne_relT;
    var age, depth, sap, grit, spread;
    var main, sub, aged, sapMod, gritSig;

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
    age = In.kr(customBus0);      // Inharmonic aging
    depth = In.kr(customBus1);    // Sub-octave mix
    sap = In.kr(customBus2);      // Slow drift
    grit = In.kr(customBus3);     // Bark texture
    spread = In.kr(customBus4);   // Stereo width

    // Sap flow: slow pitch drift
    sapMod = LFNoise1.kr(sap.linexp(0, 1, 0.02, 0.2)) * sap.linlin(0, 1, 0, 0.02);

    // Main oscillator: slightly detuned for organic feel
    main = Mix([
        Saw.ar(freq * (1 + sapMod)),
        Saw.ar(freq * 1.002 * (1 + sapMod)),
        Pulse.ar(freq * 0.999 * (1 + sapMod), 0.4) * 0.5
    ]) * 0.4;

    // Sub oscillator for depth
    sub = SinOsc.ar(freq * 0.5 * (1 + sapMod)) * depth.linlin(0, 1, 0, 0.6);

    // Age: add inharmonic partials (stretched harmonics like old wood)
    aged = Mix(Array.fill(4, { |i|
        var ratio = (i + 2) * (1 + (age * 0.1 * (i + 1).rand2));
        SinOsc.ar(freq * ratio) * (0.15 / (i + 1)) * age
    }));

    sig = main + sub + aged;

    // Grit: soft waveshaping for bark texture
    gritSig = (sig * grit.linexp(0, 1, 1, 4)).tanh;
    sig = sig.blend(gritSig, grit * 0.7);

    // Stereo spread
    sig = Pan2.ar(Mix(sig), SinOsc.kr(spread.linexp(0, 1, 0.05, 0.3).max(0.001)) * spread);

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
"  * forge_moss_root_root_drone loaded".postln;
