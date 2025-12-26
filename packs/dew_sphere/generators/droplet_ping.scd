// Droplet Ping - Light striking a perfect water sphere
// Karplus-Strong with crystalline character and spherical decay

SynthDef(\forge_dew_sphere_droplet_ping, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
    filterTypeBus, envEnabledBus, envSourceBus=0,
    clockRateBus, clockTrigBus,
    midiTrigBus=0, slotIndex=0,
    customBus0, customBus1, customBus2, customBus3, customBus4,
                                     portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento, neArr, ne_cut, ne_rq, ne_lp, ne_hp, ne_bp, ne_nt, ne_lp2, ne_off, ne_env, ne_pan, ne_panRate, ne_panWidth, ne_atkT, ne_relT;
    var sphere, glisten, ring, prism, clarity;
    var exciter, pluck, delay, decayTime, coef;
    var shimmer, prismOsc;
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
    sphere = In.kr(customBus0);     // Sphericity/purity
    glisten = In.kr(customBus1);    // Initial brightness
    ring = In.kr(customBus2);       // Ring time
    prism = In.kr(customBus3);      // Inharmonic color
    clarity = In.kr(customBus4);    // Crystal clarity

    // Exciter - short bright burst, glisten controls brightness
    exciter = WhiteNoise.ar(1) * EnvGen.ar(Env.perc(0.001, 0.01));
    exciter = HPF.ar(exciter, glisten.linexp(0, 1, 500, 4000));

    // Delay time from frequency
    delay = freq.reciprocal;

    // Decay coefficient - sphere makes it purer (less damping)
    coef = sphere.linlin(0, 1, 0.95, 0.995);
    decayTime = ring.linexp(0, 1, 0.3, 4.0);

    // Main Karplus-Strong pluck
    pluck = Pluck.ar(
        exciter,
        Impulse.ar(0),  // Trigger handled by envVCA
        0.2,
        delay.clip(0.0001, 0.2),
        decayTime,
        coef
    );

    // Prismatic inharmonic partial - slight detuning for color
    prismOsc = Pluck.ar(
        exciter * 0.5,
        Impulse.ar(0),
        0.2,
        (delay * (1 + (prism * 0.03))).clip(0.0001, 0.2),
        decayTime * 0.7,
        coef * 0.98
    ) * prism;

    // Shimmer - high frequency sparkle
    shimmer = Pluck.ar(
        exciter * 0.3,
        Impulse.ar(0),
        0.1,
        (delay * 0.5).clip(0.0001, 0.1),
        decayTime * 0.5,
        coef
    ) * clarity * 0.4;

    // Mix
    sig = pluck + prismOsc + shimmer;

    // Clarity filtering - cleaner water = more highs
    sig = LPF.ar(sig, clarity.linexp(0, 1, 4000, 18000));

    // Gentle saturation for warmth
    sig = (sig * 1.2).tanh * 0.8;
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

"  * forge_dew_sphere_droplet_ping loaded".postln;
