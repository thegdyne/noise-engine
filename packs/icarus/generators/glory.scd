// Glory -- blinding beauty of the sun up close
// Role: accent

SynthDef(\forge_icarus_glory, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                 filterTypeBus, envEnabledBus, envSourceBus=0,
                                 clockRateBus, clockTrigBus,
                                 midiTrigBus=0, slotIndex=0,
                                 customBus0, customBus1, customBus2, customBus3, customBus4,
                                     portamentoBus|

    var sig, trig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento, neArr, ne_cut, ne_rq, ne_lp, ne_hp, ne_bp, ne_nt, ne_lp2, ne_off, ne_env, ne_pan, ne_panRate, ne_panWidth, ne_atkT, ne_relT;
    var blind, awe, rays, divine, moment;
    var light, harmonics, shimmer, frozen, numRays;
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

    // Theme params
    blind = In.kr(customBus0).linlin(0, 1, 0.3, 1.0);     // Overall brightness
    awe = In.kr(customBus1).linlin(0, 1, 0.5, 6);         // FM index (harmonic richness)
    rays = In.kr(customBus2);                              // Ray count (discrete)
    divine = In.kr(customBus3).linlin(0, 1, 0.0, 0.5);    // Upper shimmer
    moment = In.kr(customBus4).linlin(0, 1, 1, 0.1);      // Time dilation (mod speed)

    // Number of light rays (2-8)
    numRays = rays.linlin(0, 1, 2, 8).round;

    // Core blinding light - FM synthesis
    light = SinOsc.ar(freq, SinOsc.ar(freq * 2.01, 0, awe));

    // Harmonic rays - additive partials
    harmonics = SinOsc.ar(freq * 2, 0, 0.3);
    harmonics = harmonics + SinOsc.ar(freq * 3, 0, 0.2 * (numRays > 2).asInteger.asInteger);
    harmonics = harmonics + SinOsc.ar(freq * 4, 0, 0.15 * (numRays > 3).asInteger.asInteger);
    harmonics = harmonics + SinOsc.ar(freq * 5, 0, 0.12 * (numRays > 4).asInteger.asInteger);
    harmonics = harmonics + SinOsc.ar(freq * 6, 0, 0.1 * (numRays > 5).asInteger.asInteger);
    harmonics = harmonics + SinOsc.ar(freq * 7, 0, 0.08 * (numRays > 6).asInteger.asInteger);
    harmonics = harmonics + SinOsc.ar(freq * 8, 0, 0.06 * (numRays > 7).asInteger.asInteger);

    // Divine shimmer - detuned high partials
    shimmer = SinOsc.ar(freq * 4 * LFNoise2.kr(moment, 0.02, 1), 0, divine);
    shimmer = shimmer + SinOsc.ar(freq * 6 * LFNoise2.kr(moment * 1.1, 0.02, 1), 0, divine * 0.7);

    // Combine in blinding glory
    sig = (light + harmonics + shimmer) * blind;

    // Wide stereo spread - enveloping light
    sig = Pan2.ar(Mix(sig), SinOsc.kr((0.3 * moment).max(0.001)).range((-0.6).clip(0,1), 0.6));
    // Output chain (inlined; avoids global helpers for NRT stability)
    sig = LeakDC.ar(sig);
    ne_panRate = (0.3 * moment).max(0.001);
    ne_panWidth = (0.6).clip(0, 1);
    ne_pan = SinOsc.kr(ne_panRate).range(ne_panWidth.neg, ne_panWidth);
    neArr = sig.asArray;
    if(neArr.size == 1, { sig = Pan2.ar(neArr[0], ne_pan) }, { sig = neArr });

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

"  * forge_icarus_glory loaded".postln;
