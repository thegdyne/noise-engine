// aurora_cave/boreal — Lightweight end-stage generator
SynthDef(\forge_aurora_cave_boreal, { |out, freqBus, customBus0|

    var sig, trig, freq, neArr, ne_cut, ne_rq, ne_lp, ne_hp, ne_bp, ne_nt, ne_lp2, ne_off, ne_env, ne_pan, ne_panRate, ne_panWidth, ne_atkT, ne_relT;
    var p = In.kr(customBus0, 5);
    var flow, curtain, pulse, color, vast;
    var layers, flowMod, pulseMod, colorMix;
    // @forge: inline_post_chain

    freq = In.kr(freqBus);
    amp = 0.2;

    flow = p[0];
    curtain = p[1];
    pulse = p[2];
    color = p[3];
    vast = p[4];

    // Flow modulation - aurora drift
    flowMod = LFNoise2.kr(flow.linexp(0, 1, 0.02, 0.3));

    // Pulse modulation - brightness waves
    pulseMod = SinOsc.kr(pulse.linexp(0, 1, 0.05, 0.5)).range(0.5, 1) ** 2;

    // Build spectral layers - aurora curtains
    layers = Array.fill(8, { |i|
        var harmonic = i + 1;
        var layerFreq = freq * harmonic * (1 + (flowMod * 0.02 * harmonic));
        var oddEven = (harmonic.odd).if(1, color);
        var layerAmp = oddEven / (harmonic ** 0.7);
        var drift = LFNoise2.kr(flow.linexp(0, 1, 0.05, 0.4) * (1 + (i * 0.1)));
        var layerPulse = SinOsc.kr(
            pulse.linexp(0, 1, 0.03, 0.3) * (1 + (i * 0.05)),
            i * 0.3
        ).range(0.4, 1);

        SinOsc.ar(layerFreq * (1 + (drift * 0.01))) * layerAmp * layerPulse * (i < (curtain * 8 + 2)).if(1, 0)
    }).sum;

    // Higher ethereal layer
    layers = layers + Array.fill(4, { |i|
        var highHarm = [9, 11, 13, 15][i];
        var highAmp = 0.1 / highHarm;
        var highDrift = LFNoise2.kr(flow.linexp(0, 1, 0.1, 0.6));
        SinOsc.ar(freq * highHarm * (1 + (highDrift * 0.02))) * highAmp * curtain * pulseMod
    }).sum;

    sig = layers * 0.25;

    // Apply overall pulse
    sig = sig * pulseMod.sqrt;

    // Soft saturation for glow
    sig = (sig * 1.5).tanh * 0.8;
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
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_aurora_cave_boreal loaded".postln;
