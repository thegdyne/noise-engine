// Granular - Micro-sample clouds
SynthDef(\granular, {
    |out=0, amp=0.5, gate=1,
    freq=220, filterType=0, cutoff=4000, res=0.3, atk=0.01, dec=0.3,
    pitch_ratio=1.0, grain_size=0.5, density=0.5, jitter=0.3, spread=0.5|
    
    var sig, env, trig, grainDur, pos;
    
    // Grain trigger with density control
    trig = Impulse.kr(density.linexp(0, 1, 5, 100));
    
    // Grain duration
    grainDur = grain_size.linexp(0, 1, 0.01, 0.2);
    
    // Position jitter
    pos = LFNoise1.kr(10) * jitter;
    
    // Granular synthesis using GrainSin (sine grains at harmonic frequencies)
    sig = GrainSin.ar(
        numChannels: 2,
        trigger: trig,
        dur: grainDur,
        freq: freq * pitch_ratio * (1 + (LFNoise1.kr(20) * jitter * 0.1)),
        pan: LFNoise1.kr(5) * spread
    );
    
    // Add some texture with noise grains
    sig = sig + GrainBuf.ar(
        numChannels: 2,
        trigger: trig,
        dur: grainDur * 0.5,
        sndbuf: LocalBuf(SampleRate.ir * 0.1).set(WhiteNoise.ar),
        rate: pitch_ratio,
        pos: pos.abs,
        pan: LFNoise1.kr(3) * spread
    ) * 0.1;
    
    // Filter
    sig = ~multiFilter.(sig, filterType, cutoff, res);
    
    // Envelope
    env = EnvGen.kr(Env.asr(atk, 1, dec), gate, doneAction: 2);
    
    Out.ar(out, sig * amp * env);
}).add;
