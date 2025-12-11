// FM - Frequency modulation synthesis
SynthDef(\fm, {
    |out=0, amp=0.5, gate=1,
    freq=220, filterType=0, cutoff=4000, res=0.3, atk=0.01, dec=0.3,
    ratio=2.0, mod_index=1.0, index_env=0.5, algorithm=0, feedback=0.1|
    
    var car, mod, modFreq, indexEnv, sig, env, fb;
    
    // Modulation frequency
    modFreq = freq * ratio.linexp(0, 1, 0.5, 8);
    
    // Index envelope (decay over time)
    indexEnv = EnvGen.kr(
        Env.perc(0.001, dec * 2),
        gate
    ) * index_env + (1 - index_env);
    
    // Feedback path
    fb = LocalIn.ar(1) * feedback * 2pi;
    
    // Modulator
    mod = SinOsc.ar(modFreq + fb) * modFreq * mod_index.linexp(0, 1, 0.1, 10) * indexEnv;
    
    // Carrier
    car = SinOsc.ar(freq + mod);
    
    // Algorithm variations (0 = simple, 1 = parallel)
    sig = SelectX.ar(algorithm, [
        car,
        (car + SinOsc.ar(freq * 1.5 + mod * 0.5)) * 0.5
    ]);
    
    // Feedback output
    LocalOut.ar(sig);
    
    // Filter
    sig = ~multiFilter.(sig, filterType, cutoff, res);
    
    // Envelope
    env = EnvGen.kr(Env.asr(atk, 1, dec), gate, doneAction: 2);
    
    Out.ar(out, (sig * amp * env) ! 2);
}).add;
