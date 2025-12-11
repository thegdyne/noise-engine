// UJT Relax - NPN/UJT/PUT relaxation oscillator
SynthDef(\ujtRelax, {
    |out=0, amp=0.5, gate=1,
    freq=220, cutoff=2000, res=0.5, atk=0.01, dec=0.3,
    rc_time=0.5, trigger_threshold=0.5, supply_voltage=0.5, feedback_amt=0.3, neg_resistance=0.3|
    
    var sig, env, oscFreq, charge, discharge, click;
    
    // Frequency from RC time constant
    oscFreq = freq * rc_time.linexp(0, 1, 0.25, 4);
    
    // Charge phase (capacitor charging through resistor)
    charge = LFSaw.ar(oscFreq, 0, 0.5, 0.5);
    
    // Trigger threshold affects duty cycle
    discharge = charge > trigger_threshold;
    
    // Negative resistance region = sharp discharge spike
    click = Impulse.ar(oscFreq) * EnvGen.ar(Env.perc(0.0001, neg_resistance.linexp(0, 1, 0.001, 0.02)));
    click = click * supply_voltage.linlin(0, 1, 0.5, 2);
    
    // Combine charge ramp and discharge spike
    sig = (charge * 0.5) + (click * 2);
    
    // Feedback adds instability
    sig = sig + (LocalIn.ar(1) * feedback_amt * 0.5);
    LocalOut.ar(DelayN.ar(sig, 0.01, 1/oscFreq * 0.5));
    
    // Filter
    sig = RLPF.ar(sig, cutoff, res);
    
    // Envelope
    env = EnvGen.kr(Env.asr(atk, 1, dec), gate, doneAction: 2);
    
    Out.ar(out, (sig * amp * env) ! 2);
}).add;
