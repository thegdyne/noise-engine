// Karplus-Strong - Plucked string physical model
SynthDef(\karplusStrong, {
    |out=0, amp=0.5, gate=1,
    freq=220, cutoff=4000, res=0.3, atk=0.001, dec=0.3,
    exciter=0.5, lpf_coef=0.5, feedback_amt=0.99, stretch=0.5, damping=0.5|
    
    var sig, exc, env, delayTime;
    
    // Delay time for pitch
    delayTime = 1 / freq;
    
    // Exciter (noise burst with variable brightness)
    exc = SelectX.ar(exciter, [
        PinkNoise.ar,
        WhiteNoise.ar,
        Impulse.ar(0) + (WhiteNoise.ar * 0.5)
    ]) * EnvGen.ar(Env.perc(0.001, 0.01));
    
    // Karplus-Strong delay line with feedback
    sig = exc + LocalIn.ar(1);
    sig = DelayC.ar(sig, 0.1, delayTime * stretch.linlin(0, 1, 0.99, 1.01));
    
    // Lowpass in feedback (string damping)
    sig = LPF.ar(sig, lpf_coef.linexp(0, 1, 500, 10000));
    sig = sig * feedback_amt.linlin(0, 1, 0.9, 0.999);
    
    // Additional damping
    sig = sig * (1 - (damping * 0.01));
    
    LocalOut.ar(sig);
    
    // Output filter
    sig = RLPF.ar(sig, cutoff, res);
    
    // Envelope
    env = EnvGen.kr(Env.asr(atk, 1, dec), gate, doneAction: 2);
    
    Out.ar(out, (sig * amp * env) ! 2);
}).add;
