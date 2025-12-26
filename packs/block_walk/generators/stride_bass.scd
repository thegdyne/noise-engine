SynthDef(\forge_block_walk_stride_bass, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                            filterTypeBus, envEnabledBus, envSourceBus=0,
                                            clockRateBus, clockTrigBus,
                                            midiTrigBus=0, slotIndex=0,
                                            customBus0, customBus1, customBus2, customBus3, customBus4,
                                     portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento, neArr, ne_cut, ne_rq, ne_lp, ne_hp, ne_bp, ne_nt, ne_lp2, ne_off, ne_env, ne_pan, ne_panRate, ne_panWidth, ne_atkT, ne_relT;
    var glide, thick, grit, bounce, warmth;
    var sub, saw1, saw2, saw3, detune, pitchEnv, envTrig;
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
    glide = In.kr(customBus0);      // GLI - legato smoothness
    thick = In.kr(customBus1);      // THK - detune spread
    grit = In.kr(customBus2);       // GRT - saturation
    bounce = In.kr(customBus3);     // BNC - pitch envelope
    warmth = In.kr(customBus4);     // WRM - sub blend

    // Additional glide smoothing layered on portamento
    freq = Lag.kr(freq, glide.linexp(0, 1, 0.001, 0.15));

    // Pitch envelope for bounce/walking feel
    envTrig = Select.ar(envSource, [
        DC.ar(0),
        Select.ar(clockRate.round, In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex, In.ar(midiTrigBus, 8))
    ]);
    pitchEnv = EnvGen.ar(Env.perc(0.001, 0.08), envTrig) * bounce.linlin(0, 1, 0, 0.15);

    // Oscillators with thickness-controlled detune
    detune = thick.linexp(0, 1, 1.001, 1.02);
    saw1 = Saw.ar(freq * (1 + pitchEnv));
    saw2 = Saw.ar(freq * detune * (1 + pitchEnv));
    saw3 = Saw.ar(freq / detune * (1 + pitchEnv));

    // Sub oscillator for warmth
    sub = SinOsc.ar(freq * 0.5) * warmth.linlin(0, 1, 0.2, 0.7);

    // Mix saws
    sig = (saw1 + (saw2 * 0.7) + (saw3 * 0.7)) * 0.4;

    // Warm saturation/grit
    sig = (sig + sub).tanh;
    sig = sig + (sig.clip2(0.3) * grit.linlin(0, 1, 0, 2));
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
"  * forge_block_walk_stride_bass loaded".postln;
