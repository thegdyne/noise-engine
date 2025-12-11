// CapSense - Charge-time capacitive sense relaxation oscillator
SynthDef(\capsense, {
    |out=0, amp=0.5, gate=1,
    freq=220, cutoff=2000, res=0.5, atk=0.01, dec=0.3,
    capacitance=0.5, dac_level=0.5, threshold=0.5, charge_cycles=0.5, filtering=0.5|
    
    var sig, env, chargeFreq, discharge;
    
    // Charge frequency based on capacitance (smaller cap = higher freq)
    chargeFreq = freq * capacitance.linexp(0, 1, 4, 0.25) * dac_level.linexp(0, 1, 0.5, 2);
    
    // Simulate charge/discharge cycle
    sig = LFSaw.ar(chargeFreq, 0, 0.5, 0.5); // Sawtooth = charging capacitor
    
    // Threshold comparator creates pulse
    discharge = (sig > threshold).lag(0.001);
    
    // Mix of charge ramp and discharge clicks
    sig = (sig * (1 - discharge)) + (discharge * Impulse.ar(chargeFreq) * 2);
    
    // Cycle-based texture
    sig = sig + (LFPulse.ar(chargeFreq / charge_cycles.linlin(0, 1, 2, 16)) * 0.1);
    
    // Internal filtering
    sig = LPF.ar(sig, filtering.linexp(0, 1, 500, 10000));
    
    // Output filter
    sig = ~multiFilter.(sig, cutoff, res);
    
    // Envelope
    env = EnvGen.kr(Env.asr(atk, 1, dec), gate, doneAction: 2);
    
    Out.ar(out, (sig * amp * env) ! 2);
}).add;
