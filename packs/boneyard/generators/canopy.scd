// CANOPY - Cracked cockpit glass, brittle transients, UV-damaged
// Role: accent
SynthDef(\forge_boneyard_canopy, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                    filterTypeBus, envEnabledBus, envSourceBus=0,
                                    clockRateBus, clockTrigBus,
                                    midiTrigBus=0, slotIndex=0,
                                    customBus0, customBus1, customBus2, customBus3, customBus4,
                                     portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento, neArr, ne_cut, ne_rq, ne_lp, ne_hp, ne_bp, ne_nt, ne_lp2, ne_off, ne_env, ne_pan, ne_panRate, ne_panWidth, ne_atkT, ne_relT;
    var cracks, thickness, uv, shatter, frame;
    var glassHit, crackResonance, shatterSpray, frameThunk, exciter;

    // Custom params
    cracks = In.kr(customBus0);     // Crack pattern spread
    thickness = In.kr(customBus1);  // Glass thickness
    uv = In.kr(customBus2);         // UV brittleness
    shatter = In.kr(customBus3);    // Shatter scatter
    frame = In.kr(customBus4);      // Frame rattle

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

    // Initial exciter
    exciter = Impulse.ar(0);

    // Glass hit - high resonant filter bank
    glassHit = Klank.ar(
        `[
            [1, 2.4, 4.2, 6.8, 9.3, 12.1],  // Glass-like inharmonic ratios
            [1, 0.6, 0.4, 0.25, 0.15, 0.1] * (1 - (uv * 0.4)),
            [1, 0.8, 0.6, 0.4, 0.3, 0.2] * uv.linexp(0, 1, 0.8, 0.1)  // UV = faster decay
        ],
        exciter * WhiteNoise.ar(1),
        freq * thickness.linexp(0, 1, 2, 0.5),  // Thicker = lower freq
        0,
        uv.linexp(0, 1, 0.5, 0.08)
    );

    // Crack resonance - multiple resonant bands spreading with crack param
    crackResonance = Mix.fill(6, { |i|
        var crackFreq, spread;
        spread = cracks.linexp(0, 1, 1.0, 2.0);
        crackFreq = freq * thickness.linexp(0, 1, 2, 0.5) * (1 + (i * 0.3 * spread));
        Ringz.ar(exciter, crackFreq, uv.linexp(0, 1, 0.3, 0.05), 1 / (i + 1));
    });
    crackResonance = crackResonance * cracks;

    // Shatter spray - burst of micro-impulses after main hit
    shatterSpray = TGrains.ar(
        2,
        Dust.ar(shatter.linexp(0, 1, 10, 200)) * EnvGen.ar(Env.perc(0.001, 0.15)),
        LocalBuf(SampleRate.ir * 0.01).collect({ |buf|
            BufWr.ar(WhiteNoise.ar(1), buf, Phasor.ar(0, 1, 0, BufFrames.ir(buf)));
            buf
        }),
        1,
        LFNoise0.kr(50).range(0, 0.01),
        LFNoise2.kr(30).range(0.002, 0.01),
        0,
        LFNoise2.kr(20).range(-1, 1),
        2
    );
    shatterSpray = HPF.ar(shatterSpray, 2000) * shatter * 0.5;

    // Frame thunk - low sub-harmonic
    frameThunk = SinOsc.ar(freq * 0.25, 0, frame);
    frameThunk = frameThunk * EnvGen.ar(Env.perc(0.001, 0.1));
    frameThunk = frameThunk + (Ringz.ar(exciter, freq * 0.5, 0.08) * frame * 0.5);

    // Combine
    sig = (glassHit * 0.4) + (crackResonance * 0.3) + shatterSpray + frameThunk;
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
"  * forge_boneyard_canopy loaded".postln;
