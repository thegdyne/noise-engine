// VCO Relax - XR2206/MAX038 style relaxation oscillator
SynthDef(\vcoRelax, {
    |out=0, amp=0.5, gate=1,
    freq=220, cutoff=2000, res=0.5, atk=0.01, dec=0.3,
    current_src=0.5, timing_cap=0.5, vco_cv=0.5, waveform=0.5, symmetry=0.5|
    
    var sig, env, baseFreq, tri, saw, pulse;
    
    // Frequency from "current source" and "capacitor"
    baseFreq = freq * current_src.linexp(0, 1, 0.25, 4) * timing_cap.linexp(0, 1, 0.5, 2);
    
    // CV modulation
    baseFreq = baseFreq * (1 + (SinOsc.kr(0.5) * vco_cv * 0.5));
    
    // Core waveforms (relaxation oscillator outputs)
    tri = LFTri.ar(baseFreq);
    saw = LFSaw.ar(baseFreq);
    pulse = LFPulse.ar(baseFreq, 0, symmetry.linlin(0, 1, 0.1, 0.9)) * 2 - 1;
    
    // Waveform crossfade
    sig = SelectX.ar(waveform * 2, [tri, saw, pulse]);
    
    // Relaxation character - slight instability
    sig = sig + (LFNoise1.ar(baseFreq * 0.1) * 0.02);
    
    // Filter
    sig = RLPF.ar(sig, cutoff, res);
    
    // Envelope
    env = EnvGen.kr(Env.asr(atk, 1, dec), gate, doneAction: 2);
    
    Out.ar(out, (sig * amp * env) ! 2);
}).add;
