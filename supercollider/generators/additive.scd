// Additive - Harmonic partial synthesis
SynthDef(\additive, {
    |out=0, amp=0.5, gate=1,
    freq=220, cutoff=4000, res=0.3, atk=0.01, dec=0.3,
    ratio_spread=1.0, amp_curve=0.7, num_partials=0.5, env_depth=0.5, spectral_tilt=0.5|
    
    var sig, env, partials, numP;
    
    numP = num_partials.linlin(0, 1, 4, 16).round;
    
    // Generate harmonic partials
    sig = Mix.fill(16, { |i|
        var harmonic = i + 1;
        var partialFreq = freq * harmonic * ratio_spread.linlin(0, 1, 0.99, 1.01);
        var partialAmp = (1 / (harmonic ** (spectral_tilt * 2 + 0.5))) * amp_curve;
        var partialEnv = EnvGen.kr(
            Env.perc(atk * (1 + (i * env_depth * 0.1)), dec * (1 + (i * 0.1))),
            gate
        );
        SinOsc.ar(partialFreq) * partialAmp * partialEnv * (i < numP)
    });
    
    // Filter
    sig = ~multiFilter.(sig, cutoff, res);
    
    // Master envelope
    env = EnvGen.kr(Env.asr(atk, 1, dec), gate, doneAction: 2);
    
    Out.ar(out, (sig * amp * env) ! 2);
}).add;
