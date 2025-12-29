SynthDef(\forge_overgrown_rebar_song, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                         filterTypeBus, envEnabledBus, envSourceBus=0,
                                         clockRateBus, clockTrigBus,
                                         midiTrigBus=0, slotIndex=0,
                                         customBus0, customBus1, customBus2, customBus3, customBus4,
                                         portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var tension, rust, ringTime, strike, rods;
    var trig, exciter, pluck1, pluck2, pluck3, noise;

    // Theme params
    tension = In.kr(customBus0);
    rust = In.kr(customBus1);
    ringTime = In.kr(customBus2);
    strike = In.kr(customBus3);
    rods = In.kr(customBus4);

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

    // Continuous triggers for drone mode (higher minimum rate)
    trig = Dust.ar(rods.linexp(0, 1, 2, 12));

    // Exciter - filtered noise burst
    exciter = WhiteNoise.ar * Decay2.ar(trig, 0.0001, strike.linexp(0, 1, 0.003, 0.025));
    exciter = HPF.ar(exciter, strike.linexp(0, 1, 200, 2000));

    // Karplus-Strong metallic strings (balanced decay times)
    pluck1 = Pluck.ar(exciter, trig, 1/20, 1/(freq * tension.linexp(0, 1, 0.8, 1.2)), ringTime.linexp(0, 1, 1, 5), rust.linexp(0, 1, 0.15, 0.45));
    pluck2 = Pluck.ar(exciter, trig, 1/20, 1/(freq * 1.002 * tension.linexp(0, 1, 0.85, 1.15)), ringTime.linexp(0, 1, 0.8, 4), rust.linexp(0, 1, 0.2, 0.5)) * 0.7;
    pluck3 = Pluck.ar(exciter, trig, 1/20, 1/(freq * 2.01), ringTime.linexp(0, 1, 0.5, 3), rust.linexp(0, 1, 0.25, 0.55)) * rods * 0.4;

    // Rust noise layer (continuous bed for drone safety)
    noise = BPF.ar(PinkNoise.ar(0.15), freq * 2, 0.4) * rust * LFNoise1.kr(0.3).range(0.3, 1);
    noise = noise + (BPF.ar(BrownNoise.ar(0.08), freq, 0.5) * 0.3);

    // Combine
    sig = [pluck1 + (pluck3 * 0.7), pluck2 + (pluck3 * 0.7)] + noise;

    // HPF to prevent low-frequency buildup
    sig = HPF.ar(sig, 50);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_overgrown_rebar_song loaded".postln;
