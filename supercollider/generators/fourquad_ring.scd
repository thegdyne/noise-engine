// 4-Quad Ring - MC1496/AD633 multiplier
SynthDef(\fourQuadRing, {
    |out=0, amp=0.5, gate=1,
    freq=220, filterType=0, cutoff=4000, res=0.3, atk=0.01, dec=0.3,
    carrier_freq=440, modulator_freq=110, gain=0.7, linearity=0.8, offset_null=0.5|
    
    var carrier, modulator, sig, env;
    
    // Carrier (reference input)
    carrier = SinOsc.ar(carrier_freq);
    
    // Modulator (signal input)
    modulator = SinOsc.ar(modulator_freq);
    
    // 4-quadrant multiplication (cleaner than diode ring)
    sig = carrier * modulator * gain;
    
    // Linearity trim (bias currents affect distortion)
    sig = sig + (sig.cubed * (1 - linearity) * 0.2);
    
    // Offset null (DC and carrier suppression)
    sig = HPF.ar(sig, 20); // Remove DC
    sig = sig + (carrier * (1 - offset_null) * 0.05); // Carrier bleed
    
    // Clean multiplier output
    sig = LeakDC.ar(sig);
    
    // Filter
    sig = ~multiFilter.(sig, filterType, cutoff, res);
    
    // Envelope
    env = EnvGen.kr(Env.asr(atk, 1, dec), gate, doneAction: 2);
    
    Out.ar(out, (sig * amp * env) ! 2);
}).add;
