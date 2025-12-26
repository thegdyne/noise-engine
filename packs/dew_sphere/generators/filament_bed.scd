// Filament Bed - Dense resonant plant filaments
// Comb filter bank excited by noise, creating silky resonant texture

SynthDef(\forge_dew_sphere_filament_bed, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
    filterTypeBus, envEnabledBus, envSourceBus=0,
    clockRateBus, clockTrigBus,
    midiTrigBus=0, slotIndex=0,
    customBus0, customBus1, customBus2, customBus3, customBus4,
                                     portamentoBus|

    var sig, trig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento, neArr, ne_cut, ne_rq, ne_lp, ne_hp, ne_bp, ne_nt, ne_lp2, ne_off, ne_env, ne_pan, ne_panRate, ne_panWidth, ne_atkT, ne_relT;
    var density, fineness, web, sway, silk;
    var exciter, combs, swayMod, delays, decayTimes;
    var comb1, comb2, comb3, comb4;
    // @forge: inline_post_chain

    // Standard bus reads
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

    // Theme params
    density = In.kr(customBus0);    // Filament density
    fineness = In.kr(customBus1);   // Strand fineness
    web = In.kr(customBus2);        // Cross-coupling
    sway = In.kr(customBus3);       // Movement
    silk = In.kr(customBus4);       // Smoothness

    // Exciter - filtered noise, density controls brightness
    exciter = PinkNoise.ar(0.5) + (WhiteNoise.ar(0.2) * density);
    exciter = LPF.ar(exciter, fineness.linexp(0, 1, 2000, 12000));

    // Sway modulation - gentle pitch wobble on filaments
    swayMod = SinOsc.kr(sway.linexp(0, 1, 0.1, 2), [0, 0.5, 1, 1.5]).range(0.998, 1.002);

    // Comb delays based on frequency - different filament lengths
    delays = [
        (freq * swayMod[0]).reciprocal,
        (freq * 1.5 * swayMod[1]).reciprocal,
        (freq * 2 * swayMod[2]).reciprocal,
        (freq * 2.5 * swayMod[3]).reciprocal
    ];

    // Decay times - silk makes them ring longer
    decayTimes = silk.linexp(0, 1, 0.1, 0.8);

    // Four comb filters at harmonic intervals
    comb1 = CombL.ar(exciter, 0.1, delays[0].clip(0.0001, 0.1), decayTimes);
    comb2 = CombL.ar(exciter, 0.1, delays[1].clip(0.0001, 0.1), decayTimes * 0.8);
    comb3 = CombL.ar(exciter, 0.1, delays[2].clip(0.0001, 0.1), decayTimes * 0.6) * fineness;
    comb4 = CombL.ar(exciter, 0.1, delays[3].clip(0.0001, 0.1), decayTimes * 0.4) * fineness;

    // Mix with density-controlled balance
    sig = (comb1 * 0.4) + (comb2 * 0.3 * density) + (comb3 * 0.2) + (comb4 * 0.1);

    // Web cross-coupling - feed back into itself slightly
    sig = sig + (DelayL.ar(sig, 0.05, 0.02) * web * 0.3);

    // Silk smoothing - gentle lowpass
    sig = LPF.ar(sig, silk.linexp(0, 1, 4000, 16000));

    // Normalize
    sig = sig * 0.7;
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

"  * forge_dew_sphere_filament_bed loaded".postln;
