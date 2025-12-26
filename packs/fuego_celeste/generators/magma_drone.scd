SynthDef(\forge_fuego_celeste_magma_drone, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                              filterTypeBus, envEnabledBus, envSourceBus=0,
                                              clockRateBus, clockTrigBus,
                                              midiTrigBus=0, slotIndex=0,
                                              customBus0, customBus1, customBus2, customBus3, customBus4,
                                     portamentoBus|

    var sig, trig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento, neArr, ne_cut, ne_rq, ne_lp, ne_hp, ne_bp, ne_nt, ne_lp2, ne_off, ne_env, ne_pan, ne_panRate, ne_panWidth, ne_atkT, ne_relT;
    var depth, churn, heat, pressure, rumble;
    var baseFreq, churnLFO, heatDrive, subOsc, chaosOsc, rumbleNoise, mixed;
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

    // Theme parameters
    depth = In.kr(customBus0);      // 0=surface, 1=deep earth
    churn = In.kr(customBus1);      // magma movement rate
    heat = In.kr(customBus2);       // harmonic brightness
    pressure = In.kr(customBus3);   // density/weight
    rumble = In.kr(customBus4);     // low tremor

    // Derive base frequency - depth pulls it lower
    baseFreq = freq * depth.linexp(0, 1, 1.0, 0.25);

    // Churning movement - slow chaotic LFO
    churnLFO = LFNoise1.kr(churn.linexp(0, 1, 0.05, 2.0)).range(0.97, 1.03);

    // Main oscillator - thick detuned saws at sub frequencies
    subOsc = Mix([
        LFSaw.ar(baseFreq * churnLFO * 0.5, 0, 0.4),
        LFSaw.ar(baseFreq * churnLFO * 0.502, 0, 0.3),
        LFSaw.ar(baseFreq * churnLFO * 1.0, 0, 0.2),
        LFPulse.ar(baseFreq * churnLFO * 0.25, 0, 0.7, 0.3)
    ]);

    // Chaos oscillator - adds organic movement
    chaosOsc = Crackle.ar(pressure.linlin(0, 1, 1.5, 1.95)) * 0.15;
    chaosOsc = LPF.ar(chaosOsc, baseFreq * 4);

    // Rumble - very low frequency noise
    rumbleNoise = LFNoise1.ar(baseFreq * 0.5) * rumble;
    rumbleNoise = LPF.ar(rumbleNoise, 80);

    // Mix sources
    mixed = (subOsc * 0.6) + (chaosOsc * pressure) + (rumbleNoise * 0.4);

    // Heat - adds harmonics via soft saturation
    heatDrive = heat.linexp(0, 1, 1.0, 8.0);
    mixed = (mixed * heatDrive).tanh / heatDrive.sqrt;

    // Add some slow stereo movement
    sig = mixed;

    // Standard post-chain
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
"  * forge_fuego_celeste_magma_drone loaded".postln;
