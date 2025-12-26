// THRESHOLD - Liminal doorway morphing
// Source: The in-between space, neither here nor there
// Role: Foreground - melodic morphing texture

SynthDef(\forge_beacon_vigil_threshold, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                     filterTypeBus, envEnabledBus, envSourceBus=0,
                                     clockRateBus, clockTrigBus,
                                     midiTrigBus=0, slotIndex=0,
                                     customBus0, customBus1, customBus2, customBus3, customBus4,
                                     portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento, neArr, ne_cut, ne_rq, ne_lp, ne_hp, ne_bp, ne_nt, ne_lp2, ne_off, ne_env, ne_pan, ne_panRate, ne_panWidth, ne_atkT, ne_relT;
    var gate, echo, edge, pass, dusk;
    var stateA, stateB, morph, doorway, reflections;
    // @forge: inline_post_chain

    // Custom params
    gate = In.kr(customBus0);  // Morph position
    echo = In.kr(customBus1);  // Reflection
    edge = In.kr(customBus2);  // Sharpness
    pass = In.kr(customBus3);  // Passage width
    dusk = In.kr(customBus4);  // Twilight character

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

    // === DSP: Threshold Liminal Space ===

    // State A: Origin - warm, grounded, simple
    stateA = SinOsc.ar(freq);
    stateA = stateA + (SinOsc.ar(freq * 0.5) * 0.4);
    stateA = stateA + (LFTri.ar(freq) * 0.2);

    // State B: Destination - bright, complex, shimmering
    stateB = Saw.ar(freq * (1 + (pass * 0.02)));
    stateB = stateB + (Pulse.ar(freq * 2, 0.3) * 0.3);
    stateB = stateB + (SinOsc.ar(freq * 3) * 0.2);
    stateB = stateB + (SinOsc.ar(freq * 5) * 0.1);
    // Shimmering detune
    stateB = stateB + (SinOsc.ar(freq * 1.005) * 0.2);

    // Morph with edge sharpness
    // Sharp edge = more sudden transition, soft = gradual
    morph = gate.pow(1 / (0.5 + (edge * 2)));

    // Doorway resonance: at threshold center, both states interfere
    doorway = (gate - 0.5).abs;
    doorway = 1 - (doorway * 2);  // Peaks at 0.5
    doorway = doorway.clip(0, 1).pow(0.5);

    // Cross-fade states
    sig = (stateA * (1 - morph)) + (stateB * morph);

    // Add interference resonance at threshold
    sig = sig + (
        Ringz.ar(
            sig * doorway * 0.3,
            freq * pass.linlin(0, 1, 1.5, 3),
            0.2
        ) * doorway * pass
    );

    // Dusk: twilight coloring - subtle FM and detuning
    sig = sig + (SinOsc.ar(freq * (1 + (SinOsc.kr(dusk * 2).range(-0.01, 0.01)))) * dusk * 0.2);
    sig = sig * (1 + (LFNoise2.kr(dusk * 3).range(-0.1, 0.1) * dusk));

    // Reflection/echo: comb resonances
    reflections = CombC.ar(sig, 0.2, 1 / (freq * 2), echo.linlin(0, 1, 0.1, 1.5));
    reflections = reflections + CombC.ar(sig, 0.2, 1 / (freq * 3), echo.linlin(0, 1, 0.05, 0.8));
    sig = sig + (reflections * echo * 0.3);

    // Gentle stereo spread based on morph position
    sig = [
        sig * (1 + ((gate - 0.5) * 0.2)),
        sig * (1 - ((gate - 0.5) * 0.2))
    ];

    // Soft clip
    sig = sig.tanh;
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
"  * forge_beacon_vigil_threshold loaded".postln;
