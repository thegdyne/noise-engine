// Diode Ring - Passive balanced modulator
SynthDef(\diodeRing, {
    |out=0, amp=0.5, gate=1,
    freq=220, cutoff=4000, res=0.3, atk=0.01, dec=0.3,
    carrier_freq=440, modulator_freq=110, input_level=0.7, balance=0.5, carrier_leak=0.1|
    
    var carrier, modulator, sig, env;
    
    // Carrier oscillator
    carrier = SinOsc.ar(carrier_freq);
    
    // Modulator oscillator
    modulator = SinOsc.ar(modulator_freq);
    
    // Ring modulation (multiplication)
    sig = carrier * modulator * input_level;
    
    // Diode imbalance adds carrier leak and asymmetry
    sig = sig + (carrier * carrier_leak * (1 - balance));
    sig = sig + (modulator * carrier_leak * balance * 0.5);
    
    // Diode nonlinearity
    sig = sig + (sig.squared * (1 - balance) * 0.1);
    
    // Filter
    sig = ~multiFilter.(sig, cutoff, res);
    
    // Envelope
    env = EnvGen.kr(Env.asr(atk, 1, dec), gate, doneAction: 2);
    
    Out.ar(out, (sig * amp * env) ! 2);
}).add;
