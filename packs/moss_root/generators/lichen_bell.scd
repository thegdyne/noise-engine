SynthDef(\forge_moss_root_lichen_bell, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                          filterTypeBus, envEnabledBus, envSourceBus=0,
                                          clockRateBus, clockTrigBus,
                                          midiTrigBus=0, slotIndex=0,
                                          customBus0, customBus1, customBus2, customBus3, customBus4,
                                     portamentoBus|

    var sig, trig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento, neArr, ne_cut, ne_rq, ne_lp, ne_hp, ne_bp, ne_nt, ne_lp2, ne_off, ne_env, ne_pan, ne_panRate, ne_panWidth, ne_atkT, ne_relT;
    var stone, ring, crust, age, spot;
    var exciter, modes, crustNoise, spotPartial;
    var modeRatios, modeAmps, ringTime;
    // @forge: inline_post_chain

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
    stone = In.kr(customBus0);
    ring = In.kr(customBus1);
    crust = In.kr(customBus2);
    age = In.kr(customBus3);
    spot = In.kr(customBus4);

    // Exciter: stone-like impulse
    exciter = Mix([
        HPF.ar(WhiteNoise.ar, stone.linexp(0, 1, 1000, 5000)),
        Impulse.ar(0) * 0.5
    ]) * EnvGen.ar(Env.perc(0.001, stone.linexp(0, 1, 0.01, 0.05)));

    // Ring time based on ring parameter
    ringTime = ring.linexp(0, 1, 0.3, 4);

    // Modal ratios - inharmonic for bell-like character, age adds stretch
    modeRatios = [1, 2.32, 3.56, 4.87, 6.23, 7.89] * (1 + (age * 0.1 * Array.series(6, 0, 0.02)));
    modeAmps = [1, 0.6, 0.4, 0.25, 0.15, 0.1];

    // Modal synthesis
    modes = Mix(Array.fill(6, { |i|
        var modeFreq = freq * modeRatios[i];
        var modeDecay = ringTime / (1 + (i * 0.3));
        Ringz.ar(exciter, modeFreq.clip(20, 15000), modeDecay) * modeAmps[i]
    })) * 0.3;

    // Add fundamental sine for body
    modes = modes + (SinOsc.ar(freq) * EnvGen.ar(Env.perc(0.001, ringTime * 0.5)) * 0.2);

    sig = modes;

    // Crust: textural noise layer
    crustNoise = BPF.ar(
        GrayNoise.ar,
        freq * 4,
        0.3
    ) * EnvGen.ar(Env.perc(0.01, crust.linexp(0, 1, 0.05, 0.3))) * crust * 0.2;
    sig = sig + crustNoise;

    // Spot: emphasized bright partial
    spotPartial = SinOsc.ar(freq * 5.5) * EnvGen.ar(Env.perc(0.001, ringTime * 0.3)) * spot * 0.15;
    sig = sig + spotPartial;

    // Subtle stereo from age-induced detuning
    sig = Pan2.ar(Mix(sig), SinOsc.kr(0.15) * age.linlin(0, 1, 0.2, 0.5));

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
"  * forge_moss_root_lichen_bell loaded".postln;
