// Neon - Neon bulb RC relaxation oscillator
SynthDef(\neonRelax, {
    |out=0, amp=0.5, gate=1,
    freq=110, cutoff=2000, res=0.5, atk=0.01, dec=0.3,
    rc_time=0.5, breakdown_v=0.7, extinguish_v=0.3, peak_v=0.8, hysteresis=0.5|
    
    var sig, env, oscFreq, charge, fire, glow;
    
    // Low frequency oscillator (neons are typically slow)
    oscFreq = freq * rc_time.linexp(0, 1, 0.1, 2) * 0.5;
    
    // Capacitor charging
    charge = LFSaw.ar(oscFreq, 0, 0.5, 0.5);
    
    // Hysteresis between breakdown and extinguish
    fire = Trig.ar(charge > breakdown_v, 1/oscFreq * (1 - extinguish_v));
    
    // Neon glow (soft orange light = filtered noise when conducting)
    glow = fire * PinkNoise.ar * peak_v;
    
    // Discharge spike
    sig = Impulse.ar(oscFreq) * EnvGen.ar(Env.perc(0.0001, hysteresis.linexp(0, 1, 0.01, 0.1)));
    
    // Combine charge ramp, glow, and spike
    sig = (charge * 0.3) + (glow * 0.5) + (sig * 2);
    
    // Filter
    sig = RLPF.ar(sig, cutoff, res);
    
    // Envelope
    env = EnvGen.kr(Env.asr(atk, 1, dec), gate, doneAction: 2);
    
    Out.ar(out, (sig * amp * env) ! 2);
}).add;
