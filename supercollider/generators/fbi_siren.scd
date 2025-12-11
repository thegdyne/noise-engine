// FBI Siren - NE556 dual-timer wail
SynthDef(\fbiSiren, {
    |out=0, amp=0.5, gate=1,
    freq=600, filterType=0, cutoff=4000, res=0.3, atk=0.01, dec=0.3,
    audio_rc=0.5, lfo_rate=2.0, mod_depth=0.6, mod_curve=0.5, drive_level=0.7|
    
    var sig, env, lfo, modFreq, vco;
    
    // First 555: LFO for modulation (~2Hz wail)
    lfo = LFTri.kr(lfo_rate);
    
    // Apply curve to modulation shape
    lfo = lfo.sign * (lfo.abs ** mod_curve.linexp(0, 1, 0.3, 3));
    
    // Second 555: VCO modulated by first timer
    modFreq = freq * audio_rc.linexp(0, 1, 0.5, 2);
    modFreq = modFreq * (1 + (lfo * mod_depth));
    
    // Square wave VCO (555 output)
    vco = Pulse.ar(modFreq, 0.5);
    
    // Add some harmonics
    sig = vco + (Pulse.ar(modFreq * 0.5, 0.5) * 0.2);
    
    // Drive (power amplifier stage)
    sig = (sig * drive_level.linexp(0, 1, 1, 4)).tanh;
    
    // Speaker resonance
    sig = BPF.ar(sig, 1200, 0.5) + (sig * 0.5);
    
    // Filter
    sig = ~multiFilter.(sig, filterType, cutoff, res);
    
    // Envelope
    env = EnvGen.kr(Env.asr(atk, 1, dec), gate, doneAction: 2);
    
    Out.ar(out, (sig * amp * env) ! 2);
}).add;
