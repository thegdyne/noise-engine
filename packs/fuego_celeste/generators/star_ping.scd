SynthDef(\forge_fuego_celeste_star_ping, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                           filterTypeBus, envEnabledBus, envSourceBus=0,
                                           clockRateBus, clockTrigBus,
                                           midiTrigBus=0, slotIndex=0,
                                           customBus0, customBus1, customBus2, customBus3, customBus4,
                                     portamentoBus|

    var sig, trig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento, neArr, ne_cut, ne_rq, ne_lp, ne_hp, ne_bp, ne_nt, ne_lp2, ne_off, ne_env, ne_pan, ne_panRate, ne_panWidth, ne_atkT, ne_relT;
    var twinkle, distance, color, size, echo;
    var modRatio, modIndex, carrier, modulator, twinkleLFO, echoSig;
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
    twinkle = In.kr(customBus0);    // scintillation rate
    distance = In.kr(customBus1);   // apparent distance
    color = In.kr(customBus2);      // warm red to cool blue
    size = In.kr(customBus3);       // apparent magnitude
    echo = In.kr(customBus4);       // cosmic reflection

    // Color determines FM ratio - red stars are warmer (lower ratio), blue stars brighter (higher)
    modRatio = color.linlin(0, 1, 1.5, 4.5);
    modIndex = color.linlin(0, 1, 2, 6);

    // FM synthesis - bell-like
    modulator = SinOsc.ar(freq * modRatio) * modIndex * freq;
    carrier = SinOsc.ar(freq + modulator);

    // Add sine fundamental for body (size)
    carrier = carrier + (SinOsc.ar(freq) * size * 0.5);

    // Add upper partials for sparkle
    carrier = carrier + (SinOsc.ar(freq * 3) * (1 - size) * 0.2);

    // Twinkle - amplitude tremolo
    twinkleLFO = SinOsc.kr(twinkle.linexp(0, 1, 2, 15)).range(0.7, 1.0);
    carrier = carrier * twinkleLFO;

    sig = carrier * 0.4;

    // Distance - high pass and level reduction
    sig = HPF.ar(sig, distance.linexp(0, 1, 100, 800));
    sig = sig * distance.linlin(0, 1, 1.0, 0.6);

    // Echo - simple comb filter reflection
    echoSig = CombL.ar(sig, 0.3, echo.linlin(0, 1, 0.05, 0.25), echo * 2);
    sig = sig + (echoSig * echo * 0.4);

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
"  * forge_fuego_celeste_star_ping loaded".postln;
