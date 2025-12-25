SynthDef(\forge_block_walk_sunset_pad, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                          filterTypeBus, envEnabledBus, envSourceBus=0,
                                          clockRateBus, clockTrigBus,
                                          midiTrigBus=0, slotIndex=0,
                                          customBus0, customBus1, customBus2, customBus3, customBus4,
                                     portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento, neArr, ne_cut, ne_rq, ne_lp, ne_hp, ne_bp, ne_nt, ne_lp2, ne_off, ne_env, ne_pan, ne_panRate, ne_panWidth, ne_atkT, ne_relT;
    var glow, haze, depth, shift, air;
    var pulse1, pulse2, pulse3, pwm1, pwm2, pwm3, detune;
    var chorus, airNoise;

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
    glow = In.kr(customBus0);       // PWM depth
    haze = In.kr(customBus1);       // Chorus
    depth = In.kr(customBus2);      // Layer count
    shift = In.kr(customBus3);      // Detune
    air = In.kr(customBus4);        // High shimmer

    // Detune amount for layers
    detune = shift.linexp(0, 1, 1.001, 1.015);

    // PWM LFOs at slightly different rates for glow
    pwm1 = SinOsc.kr(0.3).range(0.3, 0.7 - (glow * 0.2));
    pwm2 = SinOsc.kr(0.35).range(0.3 + (glow * 0.1), 0.7);
    pwm3 = SinOsc.kr(0.28).range(0.35, 0.65);

    // Three pulse layers with detune
    pulse1 = Pulse.ar(freq, pwm1);
    pulse2 = Pulse.ar(freq * detune, pwm2) * depth.linlin(0, 1, 0.3, 0.8);
    pulse3 = Pulse.ar(freq / detune, pwm3) * depth.linlin(0, 1, 0.2, 0.6);

    sig = (pulse1 + pulse2 + pulse3) * 0.25;

    // Chorus via modulated delay
    chorus = DelayC.ar(sig, 0.05,
        SinOsc.kr(0.5).range(0.005, 0.015 + (haze * 0.015))
    );
    chorus = chorus + DelayC.ar(sig, 0.05,
        SinOsc.kr(0.63, pi * 0.5).range(0.007, 0.018 + (haze * 0.012))
    );

    sig = sig + (chorus * haze.linlin(0, 1, 0.2, 0.6));

    // Air layer - filtered noise shimmer
    airNoise = BPF.ar(PinkNoise.ar(0.1), 6000 + (LFNoise1.kr(0.5) * 2000), 0.3);
    airNoise = airNoise * LFNoise1.kr(2).range(0.3, 1);
    sig = sig + (airNoise * air.linlin(0, 1, 0, 0.25));

    // Soft saturation
    sig = sig.tanh * 0.8;
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
"  * forge_block_walk_sunset_pad loaded".postln;
