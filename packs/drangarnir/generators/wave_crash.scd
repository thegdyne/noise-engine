// Wave Crash - Explosive impact of water on basalt
// Noise burst with resonant impact and spray particles

SynthDef(\forge_drangarnir_wave_crash, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                          filterTypeBus, envEnabledBus, envSourceBus=0,
                                          clockRateBus, clockTrigBus,
                                          midiTrigBus=0, slotIndex=0,
                                          customBus0, customBus1, customBus2, customBus3, customBus4,
                                     portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento, neArr, ne_cut, ne_rq, ne_lp, ne_hp, ne_bp, ne_nt, ne_lp2, ne_off, ne_env, ne_pan, ne_panRate, ne_panWidth, ne_atkT, ne_relT;
    var force, spray, rock, foam, ring;
    var impact, spraySound, foamSound, resonance;
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
    force = In.kr(customBus0);
    spray = In.kr(customBus1);
    rock = In.kr(customBus2);
    foam = In.kr(customBus3);
    ring = In.kr(customBus4);

    // Main impact - broadband noise burst
    impact = WhiteNoise.ar(force);
    impact = impact * EnvGen.ar(Env.perc(0.001, force.linlin(0, 1, 0.1, 0.4)));
    impact = LPF.ar(impact, freq * 4);

    // Rock resonance - the surface being hit
    resonance = Mix.fill(3, { |i|
        var resFreq = freq * (1 + (i * rock * 0.5));
        var ringTime = ring.linlin(0, 1, 0.05, 0.5);
        Ringz.ar(impact * 0.3, resFreq, ringTime);
    });

    // Spray particles - high frequency sparkles
    spraySound = Dust2.ar(spray.linlin(0, 1, 100, 2000)) * 0.3;
    spraySound = HPF.ar(spraySound, 4000);
    spraySound = spraySound * EnvGen.ar(Env([0, 1, 0.3, 0], [0.01, 0.1, 0.3]));

    // Foam aftermath - filtered noise sustain
    foamSound = PinkNoise.ar(foam * 0.4);
    foamSound = BPF.ar(foamSound, LFNoise1.kr(2).range(500, 2000), 0.5);
    foamSound = foamSound * EnvGen.ar(Env([0, 0, 1, 0], [0.05, 0.2, foam.linlin(0, 1, 0.3, 1.5)]));

    // Combine
    sig = impact + resonance + spraySound + foamSound;

    // Add low thump for big impacts
    sig = sig + (SinOsc.ar(freq * 0.5) * EnvGen.ar(Env.perc(0.001, 0.1)) * force * 0.3);

    // Stereo spread
    sig = Pan2.ar(Mix(sig), SinOsc.kr((0.3).max(0.001)).range(-(spray.linlin(0, 1, 0.2, 0.8).clip(0,1), (spray.linlin(0, 1, 0.2, 0.8).clip(0,1))));

    // Standard output chain
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

"  * forge_drangarnir_wave_crash loaded".postln;
