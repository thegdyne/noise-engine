// Subtractive - Classic oscillator + filter
SynthDef(\subtractive, {
    |out=0, amp=0.5, gate=1,
    freq=220, filterType=0, cutoff=2000, res=0.5, atk=0.01, dec=0.3,
    waveform=0.5, sub_osc=0.3, osc_mix=0.5, noise_amt=0.1, drive=0.3|
    
    var osc1, osc2, sub, noise, sig, env;
    
    // Main oscillators (saw <-> pulse)
    osc1 = SelectX.ar(waveform, [
        Saw.ar(freq),
        Pulse.ar(freq, 0.5)
    ]);
    osc2 = SelectX.ar(waveform, [
        Saw.ar(freq * 1.005),
        Pulse.ar(freq * 0.995, 0.4)
    ]);
    
    // Sub oscillator (one octave down)
    sub = Pulse.ar(freq * 0.5, 0.5) * sub_osc;
    
    // Noise
    noise = WhiteNoise.ar * noise_amt;
    
    // Mix
    sig = (osc1 * (1 - osc_mix)) + (osc2 * osc_mix) + sub + noise;
    
    // Drive/saturation
    sig = (sig * (1 + (drive * 4))).tanh;
    
    // Filter
    sig = ~multiFilter.(sig, filterType, cutoff, res);
    
    // Envelope
    env = EnvGen.kr(Env.asr(atk, 1, dec), gate, doneAction: 2);
    
    Out.ar(out, (sig * amp * env) ! 2);
}).add;
