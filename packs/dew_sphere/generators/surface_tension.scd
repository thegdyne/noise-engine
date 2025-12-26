// Surface Tension - Cohesive force holding droplets together
// Subtractive bed with phase-locked oscillators and slow binding modulation

SynthDef(\forge_dew_sphere_surface_tension, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
    filterTypeBus, envEnabledBus, envSourceBus=0,
    clockRateBus, clockTrigBus,
    midiTrigBus=0, slotIndex=0,
    customBus0, customBus1, customBus2, customBus3, customBus4,
                                     portamentoBus|

    var sig, trig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento, neArr, ne_cut, ne_rq, ne_lp, ne_hp, ne_bp, ne_nt, ne_lp2, ne_off, ne_env, ne_pan, ne_panRate, ne_panWidth, ne_atkT, ne_relT;
    var tension, cohesion, size, drift, air;
    var osc1, osc2, osc3, bindMod, driftMod, breath;
    var detune, phaseLink;
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
    tension = In.kr(customBus0);    // Binding force
    cohesion = In.kr(customBus1);   // Phase cohesion
    size = In.kr(customBus2);       // Droplet size
    drift = In.kr(customBus3);      // Organic drift
    air = In.kr(customBus4);        // Breathiness

    // Binding modulation - slow cohesive force
    bindMod = SinOsc.kr(tension.linexp(0, 1, 0.05, 0.5)) * tension * 0.02;

    // Organic drift - very slow random movement
    driftMod = LFNoise1.kr(drift.linexp(0, 1, 0.02, 0.2)) * drift * 0.015;

    // Detune based on size (larger = more spread)
    detune = size.linexp(0, 1, 1.001, 1.02);

    // Phase-linked oscillators - cohesion controls how tightly they track
    phaseLink = cohesion.linlin(0, 1, 0.0, 0.8);
    osc1 = VarSaw.ar(freq * (1 + bindMod + driftMod), 0, 0.5);
    osc2 = VarSaw.ar(freq * detune * (1 + (bindMod * phaseLink)), 0, 0.4);
    osc3 = VarSaw.ar(freq / detune * (1 + (bindMod * phaseLink) - driftMod), 0, 0.6);

    // Mix oscillators with size-dependent balance
    sig = (osc1 * 0.5) + (osc2 * size * 0.3) + (osc3 * (1 - size) * 0.3);

    // Breath layer - filtered noise for air
    breath = BPF.ar(PinkNoise.ar(0.3), freq * 2, 0.5) * air;
    sig = sig + breath;

    // Gentle saturation for cohesion
    sig = (sig * (1 + (tension * 0.5))).tanh * 0.8;
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

"  * forge_dew_sphere_surface_tension loaded".postln;
