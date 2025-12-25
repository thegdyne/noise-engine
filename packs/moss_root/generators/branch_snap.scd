SynthDef(\forge_moss_root_branch_snap, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                          filterTypeBus, envEnabledBus, envSourceBus=0,
                                          clockRateBus, clockTrigBus,
                                          midiTrigBus=0, slotIndex=0,
                                          customBus0, customBus1, customBus2, customBus3, customBus4,
                                     portamentoBus|

    var sig, trig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento, neArr, ne_cut, ne_rq, ne_lp, ne_hp, ne_bp, ne_nt, ne_lp2, ne_off, ne_env, ne_pan, ne_panRate, ne_panWidth, ne_atkT, ne_relT;
    var crack, wood, echo, size, dry;
    var noise, crackEnv, woodBody, bodyFreq, delayedSig;

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
    crack = In.kr(customBus0);
    wood = In.kr(customBus1);
    echo = In.kr(customBus2);
    size = In.kr(customBus3);
    dry = In.kr(customBus4);

    // Base frequency scaled by size (bigger branch = lower)
    bodyFreq = freq * size.linexp(0, 1, 2, 0.5);

    // Crack: bright noise burst with fast envelope
    crackEnv = EnvGen.ar(Env.perc(0.001, dry.linexp(0, 1, 0.08, 0.02)));
    noise = HPF.ar(WhiteNoise.ar, crack.linexp(0, 1, 2000, 8000)) * crackEnv * crack;

    // Wood body resonance: multiple modes
    woodBody = Mix([
        Ringz.ar(noise * 0.5, bodyFreq, dry.linexp(0, 1, 0.3, 0.08)) * 0.4,
        Ringz.ar(noise * 0.3, bodyFreq * 1.6, dry.linexp(0, 1, 0.25, 0.05)) * 0.3,
        Ringz.ar(noise * 0.2, bodyFreq * 2.4, dry.linexp(0, 1, 0.2, 0.04)) * 0.2
    ]) * wood;

    // Pitch bend for snap character
    sig = (noise * 0.6) + woodBody;

    // Add subtle pitched click
    sig = sig + (SinOsc.ar(bodyFreq * EnvGen.ar(Env.perc(0.001, 0.02))) * EnvGen.ar(Env.perc(0.001, 0.03)) * 0.3);

    // Forest echo: short delay with feedback
    delayedSig = CombL.ar(sig, 0.3, size.linlin(0, 1, 0.08, 0.2), echo.linlin(0, 1, 0.1, 1.5));
    sig = sig + (delayedSig * echo * 0.5);

    // Stereo spread based on echo
    sig = Pan2.ar(Mix(sig), SinOsc.kr(0.1) * echo.linlin(0, 1, 0.2, 0.6));

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
"  * forge_moss_root_branch_snap loaded".postln;
