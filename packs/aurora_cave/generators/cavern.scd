SynthDef(\forge_aurora_cave_cavern, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                        filterTypeBus, envEnabledBus, envSourceBus=0,
                                        clockRateBus, clockTrigBus,
                                        midiTrigBus=0, slotIndex=0,
                                        customBus0, customBus1, customBus2, customBus3, customBus4,
                                        portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var depth, dark, drip, echo, rumble;
    var exciter, comb1, comb2, comb3, drips, sub;

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
    amp = In.kr(~params[\amplitude]);

    // Theme params
    depth = In.kr(customBus0);
    dark = In.kr(customBus1);
    drip = In.kr(customBus2);
    echo = In.kr(customBus3);
    rumble = In.kr(customBus4);

    // Cave drip excitation
    drips = Dust.ar(drip.linexp(0, 1, 0.5, 8)) * 0.35;
    drips = Ringz.ar(drips, freq * [2, 3.2, 4.7], 0.15).sum;

    // Continuous dark noise source (boosted)
    exciter = LFNoise1.ar(100) * 0.15;
    exciter = LPF.ar(exciter, dark.linexp(0, 1, 2000, 400));
    exciter = exciter + drips;

    // Primary tuned comb - cave resonance (moderate decay)
    comb1 = CombL.ar(exciter, 0.1, freq.reciprocal, depth.linlin(0, 1, 0.8, 3.5));
    comb1 = LPF.ar(comb1, dark.linexp(0, 1, 4000, 800));

    // Secondary combs for echo complexity
    comb2 = CombL.ar(exciter, 0.15, (freq * 0.667).reciprocal, depth.linlin(0, 1, 0.6, 2.5)) * echo;
    comb2 = LPF.ar(comb2, dark.linexp(0, 1, 3000, 600));

    comb3 = CombL.ar(exciter, 0.2, (freq * 1.5).reciprocal, depth.linlin(0, 1, 0.4, 2)) * echo * 0.6;
    comb3 = LPF.ar(comb3, dark.linexp(0, 1, 2500, 500));

    // Subterranean rumble
    sub = LFNoise2.ar(rumble.linexp(0, 1, 0.5, 4)) * rumble * 0.35;
    sub = LPF.ar(sub, 80);
    sub = sub + (SinOsc.ar(freq * 0.25) * rumble * 0.28);

    // Mix layers
    sig = (comb1 * 0.5) + (comb2 * 0.3) + (comb3 * 0.2) + sub;
    sig = sig * 0.4;

    // Slight allpass diffusion for cave character
    sig = AllpassL.ar(sig, 0.1, 0.037, 0.4);
    sig = AllpassL.ar(sig, 0.1, 0.059, 0.35);

    // Output chain (with Limiter for comb feedback)
    sig = LeakDC.ar(sig);
    sig = ~stereoSpread.(sig, 0.3, 0.5);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_aurora_cave_cavern loaded".postln;
