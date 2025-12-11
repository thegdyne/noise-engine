// Modal - Resonant body simulation
SynthDef(\modal, {
    |out=0, amp=0.5, gate=1,
    freq=220, cutoff=4000, res=0.3, atk=0.001, dec=0.3,
    material=0.5, brightness=0.5, decay_time=0.5, mode_density=0.5, inharmonicity=0.2|
    
    var sig, exc, env, modes;
    
    // Exciter (impulse with variable material hardness)
    exc = Impulse.ar(0) * EnvGen.ar(Env.perc(0.0001, material.linexp(0, 1, 0.001, 0.05)));
    exc = exc + (WhiteNoise.ar * EnvGen.ar(Env.perc(0.0001, 0.002)) * (1 - material));
    
    // Modal resonances (bank of bandpass filters)
    modes = Mix.fill(8, { |i|
        var modeNum = i + 1;
        // Inharmonic mode frequencies (like bells/bars)
        var modeFreq = freq * (modeNum ** (1 + (inharmonicity * 0.5)));
        var modeDecay = decay_time.linexp(0, 1, 0.1, 4) / modeNum;
        var modeAmp = 1 / (modeNum ** (1 - brightness));
        
        Ringz.ar(exc, modeFreq.min(18000), modeDecay) * modeAmp
    }) * 0.1;
    
    sig = modes;
    
    // Output filter
    sig = RLPF.ar(sig, cutoff, res);
    
    // Envelope
    env = EnvGen.kr(Env.asr(atk, 1, dec), gate, doneAction: 2);
    
    Out.ar(out, (sig * amp * env) ! 2);
}).add;
