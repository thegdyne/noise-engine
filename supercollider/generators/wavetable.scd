// Wavetable - Morphing waveform scanning
SynthDef(\wavetable, {
    |out=0, amp=0.5, gate=1,
    freq=220, cutoff=4000, res=0.3, atk=0.01, dec=0.3,
    table_pos=0.5, scan_rate=0.2, detune=0.1, unison=0.5, interpolation=0.7|
    
    var sig, env, pos, tables;
    
    // Animated table position
    pos = table_pos + (SinOsc.kr(scan_rate.linexp(0, 1, 0.1, 5)) * 0.3);
    
    // Create different "wavetables" using crossfaded oscillators
    tables = SelectX.ar(pos.wrap(0, 3), [
        SinOsc.ar(freq),
        Saw.ar(freq),
        Pulse.ar(freq, 0.3),
        LFTri.ar(freq)
    ]);
    
    // Unison/detune
    sig = Mix.fill(3, { |i|
        var detuneAmt = detune.linexp(0, 1, 1, 1.02);
        var detuneRatio = [1, detuneAmt, 1/detuneAmt][i];
        SelectX.ar(pos.wrap(0, 3), [
            SinOsc.ar(freq * detuneRatio),
            Saw.ar(freq * detuneRatio),
            Pulse.ar(freq * detuneRatio, 0.3),
            LFTri.ar(freq * detuneRatio)
        ]) * [1, unison * 0.7, unison * 0.7][i]
    }) / (1 + unison);
    
    // Interpolation smoothing
    sig = LPF.ar(sig, interpolation.linexp(0, 1, 2000, 20000));
    
    // Filter
    sig = RLPF.ar(sig, cutoff, res);
    
    // Envelope
    env = EnvGen.kr(Env.asr(atk, 1, dec), gate, doneAction: 2);
    
    Out.ar(out, (sig * amp * env) ! 2);
}).add;
