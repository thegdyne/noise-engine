SynthDef(\forge_block_walk_leather_creak, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                             filterTypeBus, envEnabledBus, envSourceBus=0,
                                             clockRateBus, clockTrigBus,
                                             midiTrigBus=0, slotIndex=0,
                                             customBus0, customBus1, customBus2, customBus3, customBus4,
                                     portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento, neArr, ne_cut, ne_rq, ne_lp, ne_hp, ne_bp, ne_nt, ne_lp2, ne_off, ne_env, ne_pan, ne_panRate, ne_panWidth, ne_atkT, ne_relT;
    var leather, step, rub, age, movement;
    var friction, creak, body, impulse, stepRate, creakFreq;

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
    leather = In.kr(customBus0);    // Material resonance
    step = In.kr(customBus1);       // Rhythm rate
    rub = In.kr(customBus2);        // Friction
    age = In.kr(customBus3);        // Worn/creaky
    movement = In.kr(customBus4);   // Variation

    // Step impulse rate (driven by step param, but also movement for variation)
    stepRate = step.linexp(0, 1, 2, 12) * LFNoise1.kr(movement.linlin(0, 1, 0.1, 2)).range(0.7, 1.3);
    impulse = Dust.ar(stepRate);

    // Friction noise - filtered crackle
    friction = Crackle.ar(1.7 + (rub * 0.25)) * 0.3;
    friction = BPF.ar(friction, freq * 4, 0.5) * rub.linlin(0, 1, 0.2, 0.8);
    friction = friction * LFNoise1.kr(stepRate * 0.5).range(0.3, 1);

    // Creak resonances - modal filters excited by impulse
    creakFreq = freq * (1 + (LFNoise1.kr(0.5) * movement.linlin(0, 1, 0.02, 0.1)));
    creak = Ringz.ar(impulse, creakFreq * 1.5, age.linlin(0, 1, 0.05, 0.2)) * 0.3;
    creak = creak + Ringz.ar(impulse, creakFreq * 2.3, age.linlin(0, 1, 0.03, 0.15)) * 0.2;
    creak = creak + Ringz.ar(impulse, creakFreq * 3.7, age.linlin(0, 1, 0.02, 0.1)) * 0.15;

    // Body resonance from leather param
    body = Ringz.ar(impulse + (friction * 0.3), freq, leather.linlin(0, 1, 0.03, 0.12)) * 0.4;
    body = body * leather.linlin(0, 1, 0.3, 1);

    sig = friction + creak + body;

    // Age adds more high-freq creak
    sig = sig + (HPF.ar(creak, 2000) * age.linlin(0, 1, 0, 0.3));

    sig = sig.tanh * 0.7;
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
"  * forge_block_walk_leather_creak loaded".postln;
